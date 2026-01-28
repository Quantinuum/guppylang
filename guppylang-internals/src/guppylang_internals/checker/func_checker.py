"""Type checking code for top-level and nested function definitions.

For top-level functions, we take the `DefinedFunction` containing the `ast.FunctionDef`
node straight from the Python AST. We build a CFG, check it, and return a
`CheckedFunction` containing a `CheckedCFG` with type annotations.
"""

import ast
import sys
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, ClassVar, cast

from guppylang_internals.ast_util import return_nodes_in_ast, with_loc
from guppylang_internals.cfg.bb import BB
from guppylang_internals.cfg.builder import CFGBuilder
from guppylang_internals.checker.cfg_checker import CheckedCFG, check_cfg
from guppylang_internals.checker.core import Context, Globals, Place, Variable
from guppylang_internals.checker.errors.generic import UnsupportedError
from guppylang_internals.checker.unitary_checker import check_invalid_under_dagger
from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.diagnostic import Error, Help, Note
from guppylang_internals.engine import DEF_STORE, ENGINE
from guppylang_internals.error import GuppyError
from guppylang_internals.experimental import check_capturing_closures_enabled
from guppylang_internals.nodes import CheckedNestedFunctionDef, NestedFunctionDef
from guppylang_internals.tys.parsing import (
    TypeParsingCtx,
    check_function_arg,
    parse_function_arg_annotation,
    type_from_ast,
    type_with_flags_from_ast,
)
from guppylang_internals.tys.ty import (
    ExistentialTypeVar,
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    Type,
    UnitaryFlags,
    unify,
)

if sys.version_info >= (3, 12):
    from guppylang_internals.tys.parsing import parse_parameter

if TYPE_CHECKING:
    from guppylang_internals.tys.param import Parameter


@dataclass(frozen=True)
class IllegalAssignError(Error):
    title: ClassVar[str] = "Illegal assignment"
    span_label: ClassVar[str] = (
        "Variable `{var}` may not be assigned to since `{var}` is captured from an "
        "outer scope"
    )
    var: str

    @dataclass(frozen=True)
    class DefHint(Note):
        span_label: ClassVar[str] = "`{var}` defined here"
        var: str


@dataclass(frozen=True)
class MissingArgAnnotationError(Error):
    title: ClassVar[str] = "Missing type annotation"
    span_label: ClassVar[str] = "Argument requires a type annotation"


@dataclass(frozen=True)
class RecursiveSelfError(Error):
    title: ClassVar[str] = "Recursive self annotation"
    span_label: ClassVar[str] = (
        "Type of `{self_arg}` cannot recursively refer to `Self`"
    )
    self_arg: str


@dataclass(frozen=True)
class MissingReturnAnnotationError(Error):
    title: ClassVar[str] = "Missing type annotation"
    span_label: ClassVar[str] = "Return type must be annotated"

    @dataclass(frozen=True)
    class ReturnNone(Help):
        message: ClassVar[str] = (
            "Looks like `{func}` doesn't return anything. Consider annotating it with "
            "`-> None`."
        )
        func: str


@dataclass(frozen=True)
class InvalidSelfError(Error):
    title: ClassVar[str] = "Invalid self annotation"
    span_label: ClassVar[str] = "`{self_arg}` must be of type `{self_ty}`"
    self_arg: str
    self_ty: Type


@dataclass(frozen=True)
class SelfParamsShadowedError(Error):
    title: ClassVar[str] = "Shadowed generic parameters"
    span_label: ClassVar[str] = (
        "Cannot infer type for `{self_arg}` since parameter `{param}` of "
        "`{ty_defn.name}` is shadowed"
    )
    param: str
    ty_defn: "TypeDef"
    self_arg: str

    @dataclass(frozen=True)
    class ExplicitHelp(Help):
        span_label: ClassVar[str] = (
            "Consider specifying the type explicitly: `{suggestion}`"
        )

        @property
        def suggestion(self) -> str:
            parent = self._parent
            assert isinstance(parent, SelfParamsShadowedError)
            params = (
                f"[{', '.join(f'?{p.name}' for p in parent.ty_defn.params)}]"
                if parent.ty_defn.params
                else ""
            )
            return f'{parent.self_arg}: "{parent.ty_defn.name}{params}"'


def check_global_func_def(
    func_def: ast.FunctionDef, ty: FunctionType, globals: Globals
) -> CheckedCFG[Place]:
    """Type checks a top-level function definition."""
    args = func_def.args.args
    returns_none = isinstance(ty.output, NoneType)
    assert all(inp.name is not None for inp in ty.inputs)

    check_invalid_under_dagger(func_def, ty.unitary_flags)
    cfg = CFGBuilder().build(func_def.body, returns_none, globals, ty.unitary_flags)
    inputs = [
        Variable(cast("str", inp.name), inp.ty, loc, inp.flags, is_func_input=True)
        for inp, loc in zip(ty.inputs, args, strict=True)
        # Comptime inputs are turned into generic args, so are not included here
        if InputFlags.Comptime not in inp.flags
    ]
    generic_params = {
        param.name: param.with_idx(i) for i, param in enumerate(ty.params)
    }
    return check_cfg(cfg, inputs, ty.output, generic_params, func_def.name, globals)


def check_nested_func_def(
    func_def: NestedFunctionDef,
    bb: BB,
    ctx: Context,
) -> CheckedNestedFunctionDef:
    """Type checks a local (nested) function definition."""
    func_ty = check_signature(func_def, ctx.globals)
    assert func_ty.input_names is not None

    if func_ty.parametrized:
        raise GuppyError(
            UnsupportedError(func_def, "Nested generic function definitions")
        )

    # We've already built the CFG for this function while building the CFG of the
    # enclosing function
    cfg = func_def.cfg

    # Find captured variables
    parent_cfg = bb.containing_cfg
    def_ass_before = set(func_ty.input_names) | ctx.locals.keys()
    maybe_ass_before = def_ass_before | parent_cfg.maybe_ass_before[bb]
    inout_vars = inout_var_names(func_ty)
    cfg.analyze(def_ass_before, maybe_ass_before, inout_vars)
    captured = {
        x: (ctx.locals[x], using_bb.vars.used[x])
        for x, using_bb in cfg.live_before[cfg.entry_bb].items()
        if x not in func_ty.input_names and x in ctx.locals
    }

    # Capturing closures are an experimental features since they aren't supported
    # further down the stack yet
    if captured:
        _, loc = captured[next(iter(captured.keys()))]
        check_capturing_closures_enabled(loc)

    # Captured variables may never be assigned to
    for bb in cfg.bbs:
        for v, _ in captured.values():
            x = v.name
            if x in bb.vars.assigned:
                err = IllegalAssignError(bb.vars.assigned[x], x)
                err.add_sub_diagnostic(IllegalAssignError.DefHint(v.defined_at, x))
                raise GuppyError(err)

    # Construct inputs for checking the body CFG
    inputs = [v for v, _ in captured.values()] + [
        Variable(cast("str", inp.name), inp.ty, arg, inp.flags, is_func_input=True)
        for arg, inp in zip(func_def.args.args, func_ty.inputs, strict=True)
        # Comptime inputs are turned into generic args, so are not included here
        if InputFlags.Comptime not in inp.flags
    ]
    def_id = DefId.fresh()
    globals = ctx.globals

    # Check if the body contains a free (recursive) occurrence of the function name.
    # By checking if the name is free at the entry BB, we avoid false positives when
    # a user shadows the name with a local variable
    if func_def.name in cfg.live_before[cfg.entry_bb]:
        if not captured:
            # If there are no captured vars, we treat the function like a global name
            from guppylang.defs import GuppyDefinition

            from guppylang_internals.definition.function import ParsedFunctionDef

            func = ParsedFunctionDef(def_id, func_def.name, func_def, func_ty, None)
            DEF_STORE.register_def(func, None)
            ENGINE.parsed[def_id] = func
            globals.f_locals[func_def.name] = GuppyDefinition(func)
        else:
            # Otherwise, we treat it like a local name
            inputs.append(Variable(func_def.name, func_def.ty, func_def))

    checked_cfg = check_cfg(cfg, inputs, func_ty.output, {}, func_def.name, globals)
    checked_def = CheckedNestedFunctionDef(
        def_id,
        checked_cfg,
        func_ty,
        captured,
        name=func_def.name,
        args=func_def.args,
        body=func_def.body,
        decorator_list=func_def.decorator_list,
        returns=func_def.returns,
        type_comment=func_def.type_comment,
    )
    return with_loc(func_def, checked_def)


def check_signature(
    func_def: ast.FunctionDef,
    globals: Globals,
    def_id: DefId | None = None,
    unitary_flags: UnitaryFlags = UnitaryFlags.NoFlags,
) -> FunctionType:
    """Checks the signature of a function definition and returns the corresponding
    Guppy type.

    If this is a method, then the `DefId` of the associated parent type should also be
    passed. This will be used to check or infer the type annotation for the `self`
    argument.
    """
    if len(func_def.args.posonlyargs) != 0:
        raise GuppyError(
            UnsupportedError(func_def.args.posonlyargs[0], "Positional-only parameters")
        )
    if len(func_def.args.kwonlyargs) != 0:
        raise GuppyError(
            UnsupportedError(func_def.args.kwonlyargs[0], "Keyword-only parameters")
        )
    if func_def.args.vararg is not None:
        raise GuppyError(UnsupportedError(func_def.args.vararg, "Variadic args"))
    if func_def.args.kwarg is not None:
        raise GuppyError(UnsupportedError(func_def.args.kwarg, "Keyword args"))
    if func_def.args.defaults:
        raise GuppyError(
            UnsupportedError(func_def.args.defaults[0], "Default arguments")
        )
    if func_def.returns is None:
        err = MissingReturnAnnotationError(func_def)
        # TODO: Error location is incorrect
        if all(r.value is None for r in return_nodes_in_ast(func_def)):
            err.add_sub_diagnostic(
                MissingReturnAnnotationError.ReturnNone(None, func_def.name)
            )
        raise GuppyError(err)

    # Prepopulate parameter mapping when using Python 3.12 style generic syntax
    param_var_mapping: dict[str, Parameter] = {}
    if sys.version_info >= (3, 12):
        for i, param_node in enumerate(func_def.type_params):
            param = parse_parameter(param_node, i, globals, param_var_mapping)
            param_var_mapping[param.name] = param

    # Figure out if this is a method
    self_defn: TypeDef | None = None
    if def_id is not None and def_id in DEF_STORE.impl_parents:
        self_defn = cast("TypeDef", ENGINE.get_checked(DEF_STORE.impl_parents[def_id]))
        assert isinstance(self_defn, TypeDef)

    inputs = []
    ctx = TypeParsingCtx(globals, param_var_mapping, allow_free_vars=True)
    for i, inp in enumerate(func_def.args.args):
        # Special handling for `self` arguments. Note that `__new__` is excluded here
        # since it's not a method so doesn't take `self`.
        if self_defn and i == 0 and func_def.name != "__new__":
            input = parse_self_arg(inp, self_defn, ctx)
            ctx = replace(ctx, self_ty=input.ty)
        else:
            ty_ast = inp.annotation
            if ty_ast is None:
                raise GuppyError(MissingArgAnnotationError(inp))
            input = parse_function_arg_annotation(ty_ast, inp.arg, ctx)
        inputs.append(input)
    output = type_from_ast(func_def.returns, ctx)
    return FunctionType(
        inputs,
        output,
        sorted(param_var_mapping.values(), key=lambda v: v.idx),
        unitary_flags=unitary_flags,
    )


def parse_self_arg(arg: ast.arg, self_defn: TypeDef, ctx: TypeParsingCtx) -> FuncInput:
    """Handles parsing of the `self` argument on methods.

    This argument is special since its type annotation may be omitted. Furthermore, if a
    type is provided then it must match the parent type.
    """
    assert self_defn.params is not None
    if arg.annotation is None:
        return handle_implicit_self_arg(arg, self_defn, ctx)

    # If the user has provided an annotation for `self`, then we go ahead and parse it.
    # However, in the annotation the user is also allowed to use `Self`, so we have to
    # specify a `self_ty` in the context.
    self_ty_head = self_defn.check_instantiate(
        [param.to_existential()[0] for param in self_defn.params]
    )
    self_ty_placeholder = ExistentialTypeVar.fresh(
        "Self", copyable=self_ty_head.copyable, droppable=self_ty_head.droppable
    )
    assert ctx.self_ty is None
    ctx = replace(ctx, self_ty=self_ty_placeholder)
    user_ty, user_flags = type_with_flags_from_ast(arg.annotation, ctx)

    # If the user just annotates `self: Self` then we can fall back to the case where
    # no annotation is provided at all
    if user_ty == self_ty_placeholder:
        return handle_implicit_self_arg(arg, self_defn, ctx, user_flags)

    # Annotations like `self: Foo[Self]` are not allowed (would be an infinite type)
    if self_ty_placeholder in user_ty.unsolved_vars:
        raise GuppyError(RecursiveSelfError(arg.annotation, arg.arg))

    # Check that the annotation matches the parent type. We can do this by unifying with
    # the expected self type where all params are instantiated with unification vars
    subst = unify(user_ty, self_ty_head, {})
    if subst is None:
        raise GuppyError(InvalidSelfError(arg.annotation, arg.arg, self_ty_head))

    return check_function_arg(user_ty, user_flags, arg, arg.arg, ctx)


def handle_implicit_self_arg(
    arg: ast.arg,
    self_defn: TypeDef,
    ctx: TypeParsingCtx,
    flags: InputFlags = InputFlags.NoFlags,
) -> FuncInput:
    """Handles the case where no annotation for `self` is provided.

    Generates the most generic annotation that is possible by making the function as
    generic as the parent type.
    """
    # Check that the user hasn't shadowed some of the parent type parameters using a
    # Python 3.12 style parameter declaration
    assert self_defn.params is not None
    shadowed_params = [
        param for param in self_defn.params if param.name in ctx.param_var_mapping
    ]
    if shadowed_params:
        param = shadowed_params.pop()
        err = SelfParamsShadowedError(arg, param.name, self_defn, arg.arg)
        err.add_sub_diagnostic(SelfParamsShadowedError.ExplicitHelp(arg))
        raise GuppyError(err)

    # The generic params inherited from the parent type should appear first in the
    # parameter list, so we have to shift the existing ones
    for name, param in ctx.param_var_mapping.items():
        ctx.param_var_mapping[name] = param.with_idx(param.idx + len(self_defn.params))

    ctx.param_var_mapping.update({param.name: param for param in self_defn.params})
    self_args = [param.to_bound() for param in self_defn.params]
    self_ty = self_defn.check_instantiate(self_args, loc=arg)
    return check_function_arg(self_ty, flags, arg, arg.arg, ctx)


def parse_function_with_docstring(
    func_ast: ast.FunctionDef,
) -> tuple[ast.FunctionDef, str | None]:
    """Check if the first line of a function is a docstring.

    If it is, return the function with the docstring removed, plus the docstring.
    Else, return the original function and `None`
    """
    docstring = None
    match func_ast.body:
        case [doc, *xs]:
            if (
                isinstance(doc, ast.Expr)
                and isinstance(doc.value, ast.Constant)
                and isinstance(doc.value.value, str)
            ):
                docstring = doc.value.value
                func_ast.body = xs
        case _:
            pass
    return func_ast, docstring


def inout_var_names(func_ty: FunctionType) -> list[str]:
    """Returns the names of all borrowed arguments in a function type."""
    assert func_ty.input_names is not None
    return [
        x
        for inp, x in zip(func_ty.inputs, func_ty.input_names, strict=True)
        if InputFlags.Inout in inp.flags
    ]
