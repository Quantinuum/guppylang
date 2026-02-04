import ast
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from types import ModuleType

from guppylang_internals.ast_util import (
    AstNode,
    set_location_from,
    shift_loc,
)
from guppylang_internals.cfg.builder import is_comptime_expression
from guppylang_internals.checker.core import Context, Globals, Locals, PythonObject
from guppylang_internals.checker.errors.generic import ExpectedError, UnsupportedError
from guppylang_internals.definition.common import Definition
from guppylang_internals.definition.parameter import ParamDef
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.engine import ENGINE
from guppylang_internals.error import GuppyError
from guppylang_internals.tys.arg import Argument, ConstArg, TypeArg
from guppylang_internals.tys.builtin import CallableTypeDef, SelfTypeDef, bool_type
from guppylang_internals.tys.const import ConstValue
from guppylang_internals.tys.errors import (
    CallableComptimeError,
    ComptimeArgShadowError,
    FlagNotAllowedError,
    FreeTypeVarError,
    HigherKindedTypeVarError,
    IllegalComptimeTypeArgError,
    InvalidCallableTypeError,
    InvalidFlagError,
    InvalidTypeArgError,
    InvalidTypeError,
    LinearComptimeError,
    LinearConstParamError,
    ModuleMemberNotFoundError,
    NonLinearOwnedError,
    SelfTyNotInMethodError,
    WrongNumberOfTypeArgsError,
)
from guppylang_internals.tys.param import ConstParam, Parameter, TypeParam
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
    TupleType,
    Type,
)


@dataclass(frozen=True)
class TypeParsingCtx:
    """Context for parsing types from AST nodes."""

    #: The globals variable context
    globals: Globals

    #: The available type parameters indexed by name
    param_var_mapping: dict[str, Parameter] = field(default_factory=dict)

    #: Whether a previously unseen type parameters is allowed to be bound (i.e. is
    #: allowed to be added to `param_var_mapping`
    allow_free_vars: bool = False

    #: When parsing types in the signature or body of a method, we also need access to
    #: the type this method belongs to in order to resolve `Self` annotations.
    self_ty: Type | None = None


def arg_from_ast(node: AstNode, ctx: TypeParsingCtx) -> Argument:
    """Turns an AST expression into an argument."""
    from guppylang_internals.checker.cfg_checker import VarNotDefinedError

    # A single (possibly qualified) identifier
    if defn := _try_parse_defn(node, ctx.globals):
        return _arg_from_instantiated_defn(defn, [], node, ctx)

    # An identifier referring to a quantified variable
    if isinstance(node, ast.Name):
        if node.id in ctx.param_var_mapping:
            return ctx.param_var_mapping[node.id].to_bound()
        raise GuppyError(VarNotDefinedError(node, node.id))

    # A parametrised type, e.g. `list[??]`
    if isinstance(node, ast.Subscript) and (
        defn := _try_parse_defn(node.value, ctx.globals)
    ):
        arg_nodes = (
            node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
        )
        return _arg_from_instantiated_defn(defn, arg_nodes, node, ctx)

    # We allow tuple types to be written as `(int, bool)`
    if isinstance(node, ast.Tuple):
        ty = TupleType([type_from_ast(el, ctx) for el in node.elts])
        return TypeArg(ty)

    # Literals
    if isinstance(node, ast.Constant):
        match node.value:
            # `None` is represented as a `ast.Constant` node with value `None`
            case None:
                return TypeArg(NoneType())
            case bool(v):
                return ConstArg(ConstValue(bool_type(), v))
            # Integer literals are turned into nat args.
            # TODO: To support int args, we need proper inference logic here
            #   See https://github.com/quantinuum/guppylang/issues/1030
            case int(v) if v >= 0:
                nat_ty = NumericType(NumericType.Kind.Nat)
                return ConstArg(ConstValue(nat_ty, v))
            case float(v):
                float_ty = NumericType(NumericType.Kind.Float)
                return ConstArg(ConstValue(float_ty, v))
            # String literals are ignored for now since they could also be stringified
            # types.
            # TODO: To support string args, we need proper inference logic here
            #   See https://github.com/quantinuum/guppylang/issues/1030
            case str(_):
                pass

    # Py-expressions can also be used to specify static numbers
    if comptime_expr := is_comptime_expression(node):
        from guppylang_internals.checker.expr_checker import eval_comptime_expr

        v = eval_comptime_expr(comptime_expr, Context(ctx.globals, Locals({}), {}))
        if isinstance(v, int):
            nat_ty = NumericType(NumericType.Kind.Nat)
            return ConstArg(ConstValue(nat_ty, v))
        else:
            raise GuppyError(IllegalComptimeTypeArgError(node, v))

    # Finally, we also support delayed annotations in strings
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        node = _parse_delayed_annotation(node.value, node)
        return arg_from_ast(node, ctx)

    raise GuppyError(InvalidTypeArgError(node))


def _try_parse_defn(node: AstNode, globals: Globals) -> Definition | None:
    """Tries to parse a (possibly qualified) name into a global definition."""
    from guppylang.defs import GuppyDefinition

    from guppylang_internals.checker.cfg_checker import VarNotDefinedError

    match node:
        case ast.Name(id=x):
            if x not in globals:
                return None
            defn = globals[x]
            if isinstance(defn, PythonObject):
                return None
            return defn
        case ast.Attribute(value=ast.Name(id=module_name) as value, attr=x):
            if module_name not in globals:
                raise GuppyError(VarNotDefinedError(value, module_name))
            match globals[module_name]:
                case PythonObject(ModuleType() as module):
                    if x in module.__dict__:
                        val = module.__dict__[x]
                        if isinstance(val, GuppyDefinition):
                            return ENGINE.get_parsed(val.id)
                    raise GuppyError(
                        ModuleMemberNotFoundError(node, module.__name__, x)
                    )
                case _:
                    raise GuppyError(ExpectedError(value, "a module"))
        case _:
            return None


def _arg_from_instantiated_defn(
    defn: Definition, arg_nodes: list[ast.expr], node: AstNode, ctx: TypeParsingCtx
) -> Argument:
    """Parses a globals definition with type args into an argument."""
    match defn:
        # Special case for the `Callable` type
        case CallableTypeDef():
            return TypeArg(_parse_callable_type(arg_nodes, node, ctx))
            # Special case for the `Callable` type
        case SelfTypeDef():
            return TypeArg(_parse_self_type(arg_nodes, node, ctx))
        # Either a defined type (e.g. `int`, `bool`, ...)
        case TypeDef() as defn:
            args = [arg_from_ast(arg_node, ctx) for arg_node in arg_nodes]
            ty = defn.check_instantiate(args, node)
            return TypeArg(ty)
        # Or a parameter (e.g. `T`, `n`, ...)
        case ParamDef() as defn:
            # We don't allow parametrised variables like `T[int]`
            if arg_nodes:
                raise GuppyError(HigherKindedTypeVarError(node, defn))
            if defn.name not in ctx.param_var_mapping:
                if ctx.allow_free_vars:
                    ctx.param_var_mapping[defn.name] = defn.to_param(
                        len(ctx.param_var_mapping)
                    )
                else:
                    raise GuppyError(FreeTypeVarError(node, defn))
            return ctx.param_var_mapping[defn.name].to_bound()
        case defn:
            err = ExpectedError(node, "a type", got=f"{defn.description} `{defn.name}`")
            raise GuppyError(err)


def _parse_delayed_annotation(ast_str: str, node: ast.Constant) -> ast.expr:
    """Parses a delayed type annotation in a string."""
    try:
        [stmt] = ast.parse(ast_str).body
        if not isinstance(stmt, ast.Expr):
            raise GuppyError(InvalidTypeError(node))
        set_location_from(stmt, loc=node)
        shift_loc(
            stmt,
            delta_lineno=node.lineno - 1,  # -1 since lines start at 1
            delta_col_offset=node.col_offset + 1,  # +1 to remove the `"`
        )
    except (SyntaxError, ValueError):
        raise GuppyError(InvalidTypeError(node)) from None
    else:
        return stmt.value


def _parse_callable_type(
    args: list[ast.expr], loc: AstNode, ctx: TypeParsingCtx
) -> FunctionType:
    """Helper function to parse a `Callable[[<arguments>], <return type>]` type."""
    err = InvalidCallableTypeError(loc)
    if len(args) != 2:
        raise GuppyError(err)
    [inputs, output] = args
    if not isinstance(inputs, ast.List):
        raise GuppyError(err)
    inputs = [parse_function_arg_annotation(inp, None, ctx) for inp in inputs.elts]
    output = type_from_ast(output, ctx)
    return FunctionType(inputs, output)


def _parse_self_type(args: list[ast.expr], loc: AstNode, ctx: TypeParsingCtx) -> Type:
    """Helper function to parse a `Self` type.

    Returns the actual type `Self` refers to or emits a user error if we're not inside
    a method.
    """
    if ctx.self_ty is None:
        raise GuppyError(SelfTyNotInMethodError(loc))

    # We don't allow specifying generic arguments of `Self`. This matches the behaviour
    # of Python.
    if args:
        raise GuppyError(WrongNumberOfTypeArgsError(loc, 0, len(args), "Self"))
    return ctx.self_ty


def parse_function_arg_annotation(
    annotation: ast.expr, name: str | None, ctx: TypeParsingCtx
) -> FuncInput:
    """Parses an annotation in the input of a function type."""
    ty, flags = type_with_flags_from_ast(annotation, ctx)
    return check_function_arg(ty, flags, annotation, name, ctx)


def check_function_arg(
    ty: Type, flags: InputFlags, loc: AstNode, name: str | None, ctx: TypeParsingCtx
) -> FuncInput:
    """Given a function input type and its user-provided flags, checks if the flags
    are valid and inserts implicit flags."""
    if InputFlags.Owned in flags and ty.copyable:
        raise GuppyError(NonLinearOwnedError(loc, ty))
    if not ty.copyable and InputFlags.Owned not in flags:
        flags |= InputFlags.Inout
    if InputFlags.Comptime in flags:
        if name is None:
            raise GuppyError(CallableComptimeError(loc))

        # Make sure we're not shadowing a type variable with the same name that was
        # already used on the left. E.g
        #
        #    n = guppy.type_var("n")
        #    def foo(xs: array[int, n], n: nat @comptime)
        #
        # TODO: In principle we could lift this restriction by tracking multiple
        #  params referring to the same name in `param_var_mapping`, but not sure if
        #  this would be worth it...
        if name in ctx.param_var_mapping:
            raise GuppyError(ComptimeArgShadowError(loc, name))
        ctx.param_var_mapping[name] = ConstParam(
            len(ctx.param_var_mapping), name, ty, from_comptime_arg=True
        )
    return FuncInput(ty, flags, name)


if sys.version_info >= (3, 12):

    def parse_parameter(
        node: ast.type_param,
        idx: int,
        globals: Globals,
        param_var_mapping: dict[str, Parameter],
        allow_free_vars: bool = False,
    ) -> Parameter:
        """Parses a `Variable: Bound` generic type parameter declaration."""
        if isinstance(node, ast.TypeVarTuple | ast.ParamSpec):
            raise GuppyError(UnsupportedError(node, "Variadic generic parameters"))
        assert isinstance(node, ast.TypeVar)

        match node.bound:
            # No bound means it's a linear type parameter
            case None:
                return TypeParam(
                    idx, node.name, must_be_copyable=False, must_be_droppable=False
                )
            # Special `Copy` or `Drop` bounds for types
            case ast.Name(id="Copy"):
                return TypeParam(
                    idx, node.name, must_be_copyable=True, must_be_droppable=False
                )
            case ast.Name(id="Drop"):
                return TypeParam(
                    idx, node.name, must_be_copyable=False, must_be_droppable=True
                )
            # Copy and drop is annotated as `T: (Copy, Drop)`
            # TODO: Should we also allow `T: Copy + Drop`? Mypy would complain about it
            case ast.Tuple(elts=[ast.Name(id=id1), ast.Name(id=id2)]) if {id1, id2} == {
                "Copy",
                "Drop",
            }:
                return TypeParam(
                    idx, node.name, must_be_copyable=True, must_be_droppable=True
                )
            # Otherwise, it must be a const parameter
            case bound:
                # For now, we don't allow the types of const params to refer to previous
                # parameters, so we pass an empty dict as the `param_var_mapping`.
                # TODO: In the future we might want to allow stuff like
                #   `def foo[T, XS: array[T, 42]]` and so on
                ctx = TypeParsingCtx(globals, param_var_mapping, allow_free_vars)
                ty = type_from_ast(bound, ctx)
                if not ty.copyable or not ty.droppable:
                    raise GuppyError(LinearConstParamError(bound, ty))
                return ConstParam(idx, node.name, ty)


_type_param = TypeParam(0, "T", False, False)


def type_with_flags_from_ast(
    node: AstNode, ctx: TypeParsingCtx
) -> tuple[Type, InputFlags]:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.MatMult):
        ty, flags = type_with_flags_from_ast(node.left, ctx)
        match node.right:
            case ast.Name(id="owned"):
                if ty.copyable:
                    raise GuppyError(NonLinearOwnedError(node.right, ty))
                flags |= InputFlags.Owned
            case ast.Name(id="comptime"):
                flags |= InputFlags.Comptime
                if not ty.copyable or not ty.droppable:
                    raise GuppyError(LinearComptimeError(node.right, ty))
            case _:
                raise GuppyError(InvalidFlagError(node.right))
        return ty, flags
    # We also need to handle the case that this could be a delayed string annotation
    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        node = _parse_delayed_annotation(node.value, node)
        return type_with_flags_from_ast(node, ctx)
    else:
        # Parse an argument and check that it's valid for a `TypeParam`
        arg = arg_from_ast(node, ctx)
        tyarg = _type_param.check_arg(arg, node)
        return tyarg.ty, InputFlags.NoFlags


def type_from_ast(node: AstNode, ctx: TypeParsingCtx) -> Type:
    """Turns an AST expression into a Guppy type."""
    ty, flags = type_with_flags_from_ast(node, ctx)
    if flags != InputFlags.NoFlags:
        # Users shouldn't be able to set this
        # Ignore needed for Python 3.10 mypy compatibility with Flag enums
        assert InputFlags.Inout not in flags  # type: ignore[operator, unused-ignore]
        raise GuppyError(FlagNotAllowedError(node))
    return ty


def type_row_from_ast(node: ast.expr, ctx: TypeParsingCtx) -> Sequence[Type]:
    """Turns an AST expression into a Guppy type row.

    This is needed to interpret the return type annotation of functions.
    """
    # The return type `-> None` is represented in the ast as `ast.Constant(value=None)`
    if isinstance(node, ast.Constant) and node.value is None:
        return []
    ty = type_from_ast(node, ctx)
    if isinstance(ty, TupleType):
        return ty.element_types
    else:
        return [ty]
