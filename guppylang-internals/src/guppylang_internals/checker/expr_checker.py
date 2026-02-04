"""Type checking and synthesizing code for expressions.

Operates on expressions in a basic block after CFG construction. In particular, we
assume that expressions that involve control flow (i.e. short-circuiting and ternary
expressions) have been removed during CFG construction.

Furthermore, we assume that assignment expressions with the walrus operator := have
been turned into regular assignments and are no longer present. As a result, expressions
are assumed to be side effect free, in the sense that they do not modify the variables
available in the type checking context.

We may alter/desugar AST nodes during type checking. In particular, we turn `ast.Name`
nodes into either `LocalName` or `GlobalName` nodes and `ast.Call` nodes are turned into
`LocalCall` or `GlobalCall` nodes. Furthermore, all nodes in the resulting AST are
annotated with their type.

Expressions can be checked against a given type by the `ExprChecker`, raising a type
error if the expressions doesn't have the expected type. Checking is used for annotated
assignments, return values, and function arguments. Alternatively, the `ExprSynthesizer`
can be used to infer a type for an expression.
"""

import ast
import copy
import sys
import traceback
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import replace
from types import ModuleType
from typing import TYPE_CHECKING, Any, NoReturn, cast

from typing_extensions import assert_never

from guppylang_internals.ast_util import (
    AstNode,
    AstVisitor,
    breaks_in_loop,
    get_type,
    get_type_opt,
    return_nodes_in_ast,
    with_loc,
    with_type,
)
from guppylang_internals.cfg.builder import is_tmp_var, tmp_vars
from guppylang_internals.checker.core import (
    ComptimeVariable,
    Context,
    DummyEvalDict,
    FieldAccess,
    Globals,
    Locals,
    Place,
    PythonObject,
    SetitemCall,
    SubscriptAccess,
    TupleAccess,
    Variable,
)
from guppylang_internals.checker.errors.comptime_errors import (
    ComptimeExprEvalError,
    ComptimeExprIncoherentListError,
    ComptimeExprNotCPythonError,
    ComptimeExprNotStaticError,
    ComptimeUnknownError,
    IllegalComptimeExpressionError,
)
from guppylang_internals.checker.errors.generic import ExpectedError, UnsupportedError
from guppylang_internals.checker.errors.linearity import NonDroppableForBreakError
from guppylang_internals.checker.errors.type_errors import (
    AttributeNotFoundError,
    BadProtocolError,
    BinaryOperatorNotDefinedError,
    ConstMismatchError,
    IllegalConstant,
    IntOverflowError,
    ModuleMemberNotFoundError,
    NonLinearInstantiateError,
    NotCallableError,
    ParameterInferenceError,
    TupleIndexOutOfBoundsError,
    TypeApplyNotGenericError,
    TypeInferenceError,
    TypeMismatchError,
    UnaryOperatorNotDefinedError,
    WrongNumberOfArgsError,
)
from guppylang_internals.definition.common import Definition
from guppylang_internals.definition.parameter import ParamDef
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.definition.value import CallableDef, ValueDef
from guppylang_internals.error import (
    GuppyError,
    GuppyTypeError,
    GuppyTypeInferenceError,
    InternalGuppyError,
)
from guppylang_internals.experimental import (
    check_function_tensors_enabled,
    check_lists_enabled,
)
from guppylang_internals.nodes import (
    ComptimeExpr,
    DesugaredGenerator,
    DesugaredGeneratorExpr,
    DesugaredListComp,
    FieldAccessAndDrop,
    GenericParamValue,
    GlobalName,
    IterNext,
    LocalCall,
    MakeIter,
    PartialApply,
    PlaceNode,
    SubscriptAccessAndDrop,
    TensorCall,
    TupleAccessAndDrop,
    TypeApply,
)
from guppylang_internals.span import Span, to_span
from guppylang_internals.tys.arg import TypeArg
from guppylang_internals.tys.builtin import (
    bool_type,
    float_type,
    frozenarray_type,
    get_element_type,
    int_type,
    is_bool_type,
    is_frozenarray_type,
    is_list_type,
    is_sized_iter_type,
    list_type,
    nat_type,
    option_type,
    string_type,
)
from guppylang_internals.tys.const import Const, ConstValue
from guppylang_internals.tys.param import ConstParam, TypeParam, check_all_args
from guppylang_internals.tys.parsing import arg_from_ast
from guppylang_internals.tys.subst import Inst, Subst
from guppylang_internals.tys.ty import (
    ExistentialTypeVar,
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
    OpaqueType,
    StructType,
    TupleType,
    Type,
    TypeBase,
    function_tensor_signature,
    parse_function_tensor,
    unify,
)
from guppylang_internals.tys.var import ExistentialVar

if TYPE_CHECKING:
    from guppylang_internals.diagnostic import SubDiagnostic

# Mapping from unary AST op to dunder method and display name
unary_table: dict[type[ast.unaryop], tuple[str, str]] = {
    ast.UAdd:   ("__pos__",    "+"),
    ast.USub:   ("__neg__",    "-"),
    ast.Invert: ("__invert__", "~"),
}  # fmt: skip

# Mapping from binary AST op to left dunder method, right dunder method and display name
AstOp = ast.operator | ast.cmpop
binary_table: dict[type[AstOp], tuple[str, str, str]] = {
    ast.Add:      ("__add__",      "__radd__",      "+"),
    ast.Sub:      ("__sub__",      "__rsub__",      "-"),
    ast.Mult:     ("__mul__",      "__rmul__",      "*"),
    ast.Div:      ("__truediv__",  "__rtruediv__",  "/"),
    ast.FloorDiv: ("__floordiv__", "__rfloordiv__", "//"),
    ast.Mod:      ("__mod__",      "__rmod__",      "%"),
    ast.Pow:      ("__pow__",      "__rpow__",      "**"),
    ast.LShift:   ("__lshift__",   "__rlshift__",   "<<"),
    ast.RShift:   ("__rshift__",   "__rrshift__",   ">>"),
    ast.BitOr:    ("__or__",       "__ror__",       "|"),
    ast.BitXor:   ("__xor__",      "__rxor__",      "^"),
    ast.BitAnd:   ("__and__",      "__rand__",      "&"),
    ast.MatMult:  ("__matmul__",   "__rmatmul__",   "@"),
    ast.Eq:       ("__eq__",       "__eq__",        "=="),
    ast.NotEq:    ("__ne__",       "__ne__",        "!="),
    ast.Lt:       ("__lt__",       "__gt__",        "<"),
    ast.LtE:      ("__le__",       "__ge__",        "<="),
    ast.Gt:       ("__gt__",       "__lt__",        ">"),
    ast.GtE:      ("__ge__",       "__le__",        ">="),
}  # fmt: skip


class ExprChecker(AstVisitor[tuple[ast.expr, Subst]]):
    """Checks an expression against a type and produces a new type-annotated AST.

    The type may contain free variables that the checker will try to solve. Note that
    the checker will fail, if some free variables cannot be inferred.
    """

    ctx: Context

    # Name for the kind of term we are currently checking against (used in errors).
    # For example, "argument", "return value", or in general "expression".
    _kind: str

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self._kind = "expression"

    def _fail(
        self,
        expected: Type,
        actual: ast.expr | Type,
        loc: AstNode | None = None,
    ) -> NoReturn:
        """Raises a type error indicating that the type doesn't match."""
        if not isinstance(actual, TypeBase):
            loc = loc or actual
            _, actual = self._synthesize(actual, allow_free_vars=True)
        if loc is None:
            raise InternalGuppyError("Failure location is required")
        raise GuppyTypeError(TypeMismatchError(loc, expected, actual))

    def check(
        self, expr: ast.expr, ty: Type, kind: str = "expression"
    ) -> tuple[ast.expr, Subst]:
        """Checks an expression against a type.

        The type may have free type variables which will try to be resolved. Returns
        a new desugared expression with type annotations and a substitution with the
        resolved type variables.
        """
        # If we already have a type for the expression, we just have to match it against
        # the target
        if actual := get_type_opt(expr):
            expr, subst, inst = check_type_against(actual, ty, expr, self.ctx, kind)
            if inst:
                expr = with_loc(expr, TypeApply(expr, inst))
            return with_type(ty.substitute(subst), expr), subst

        # When checking against a variable, we have to synthesize
        if isinstance(ty, ExistentialTypeVar):
            expr, syn_ty = self._synthesize(expr, allow_free_vars=False)
            return with_type(syn_ty, expr), {ty: syn_ty}

        # Otherwise, invoke the visitor
        old_kind = self._kind
        self._kind = kind or self._kind
        expr, subst = self.visit(expr, ty)
        self._kind = old_kind
        return with_type(ty.substitute(subst), expr), subst

    def _synthesize(
        self, node: ast.expr, allow_free_vars: bool
    ) -> tuple[ast.expr, Type]:
        """Invokes the type synthesiser"""
        return ExprSynthesizer(self.ctx).synthesize(node, allow_free_vars)

    def visit_Constant(self, node: ast.Constant, ty: Type) -> tuple[ast.expr, Subst]:
        act = python_value_to_guppy_type(node.value, node, self.ctx.globals, ty)
        if act is None:
            raise GuppyError(IllegalConstant(node, type(node.value)))
        node, subst, inst = check_type_against(act, ty, node, self.ctx, self._kind)
        assert inst == [], "Const values are not generic"
        return node, subst

    def visit_Tuple(self, node: ast.Tuple, ty: Type) -> tuple[ast.expr, Subst]:
        if not isinstance(ty, TupleType) or len(ty.element_types) != len(node.elts):
            return self._fail(ty, node)
        subst: Subst = {}
        for i, el in enumerate(node.elts):
            node.elts[i], s = self.check(el, ty.element_types[i].substitute(subst))
            subst |= s
        return node, subst

    def visit_List(self, node: ast.List, ty: Type) -> tuple[ast.expr, Subst]:
        check_lists_enabled(node)
        if not is_list_type(ty):
            return self._fail(ty, node)
        el_ty = get_element_type(ty)
        subst: Subst = {}
        for i, el in enumerate(node.elts):
            node.elts[i], s = self.check(el, el_ty.substitute(subst))
            subst |= s
        return node, subst

    def visit_DesugaredListComp(
        self, node: DesugaredListComp, ty: Type
    ) -> tuple[ast.expr, Subst]:
        if not is_list_type(ty):
            return self._fail(ty, node)
        node.generators, node.elt, elt_ty = synthesize_comprehension(
            node, node.generators, node.elt, self.ctx
        )
        subst = unify(get_element_type(ty), elt_ty, {})
        if subst is None:
            actual = list_type(elt_ty)
            return self._fail(ty, actual, node)
        return node, subst

    def visit_Call(self, node: ast.Call, ty: Type) -> tuple[ast.expr, Subst]:
        if len(node.keywords) > 0:
            raise GuppyError(UnsupportedError(node.keywords[0], "Keyword arguments"))
        node.func, func_ty = self._synthesize(node.func, allow_free_vars=False)

        # First handle direct calls of user-defined functions and extension functions
        if isinstance(node.func, GlobalName):
            defn = self.ctx.globals[node.func.def_id]
            if isinstance(defn, CallableDef):
                return defn.check_call(node.args, ty, node, self.ctx)

        # When calling a `PartialApply` node, we just move the args into this call
        if isinstance(node.func, PartialApply):
            node.args = [*node.func.args, *node.args]
            node.func = node.func.func
            return self.visit_Call(node, ty)

        # Otherwise, it must be a function as a higher-order value - something
        # whose type is either a FunctionType or a Tuple of FunctionTypes
        if isinstance(func_ty, FunctionType):
            args, return_ty, inst = check_call(func_ty, node.args, ty, node, self.ctx)
            check_inst(func_ty, inst, node)
            node.func = instantiate_poly(node.func, func_ty, inst)
            return with_loc(node, LocalCall(func=node.func, args=args)), return_ty

        if isinstance(func_ty, TupleType) and (
            function_elements := parse_function_tensor(func_ty)
        ):
            check_function_tensors_enabled(node.func)
            if any(f.parametrized for f in function_elements):
                raise GuppyError(
                    UnsupportedError(node.func, "Polymorphic function tensors")
                )

            tensor_ty = function_tensor_signature(function_elements)

            processed_args, subst, inst = check_call(
                tensor_ty, node.args, ty, node, self.ctx
            )
            assert len(inst) == 0
            return with_loc(
                node,
                TensorCall(func=node.func, args=processed_args, tensor_ty=tensor_ty),
            ), subst

        elif callee := self.ctx.globals.get_instance_func(func_ty, "__call__"):
            return callee.check_call(node.args, ty, node, self.ctx)
        else:
            raise GuppyTypeError(NotCallableError(node.func, func_ty))

    def visit_ComptimeExpr(
        self, node: ComptimeExpr, ty: Type
    ) -> tuple[ast.expr, Subst]:
        python_val = eval_comptime_expr(node, self.ctx)
        if act := python_value_to_guppy_type(
            python_val, node.value, self.ctx.globals, ty
        ):
            subst = unify(ty, act, {})
            if subst is None:
                self._fail(ty, act, node)
            act = act.substitute(subst)
            subst = {x: s for x, s in subst.items() if x in ty.unsolved_vars}
            return with_type(act, with_loc(node, ast.Constant(value=python_val))), subst

        raise GuppyError(IllegalComptimeExpressionError(node.value, type(python_val)))

    def generic_visit(self, node: ast.expr, ty: Type) -> tuple[ast.expr, Subst]:
        # Try to synthesize and then check if we can unify it with the given type
        node, synth = self._synthesize(node, allow_free_vars=False)
        node, subst, inst = check_type_against(synth, ty, node, self.ctx, self._kind)

        # Apply instantiation of quantified type variables
        if inst:
            node = with_loc(node, TypeApply(node, inst))

        return node, subst


class ExprSynthesizer(AstVisitor[tuple[ast.expr, Type]]):
    ctx: Context

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx

    def synthesize(
        self, node: ast.expr, allow_free_vars: bool = False
    ) -> tuple[ast.expr, Type]:
        """Tries to synthesise a type for the given expression.

        Also returns a new desugared expression with type annotations.
        """
        if ty := get_type_opt(node):
            return node, ty
        node, ty = self.visit(node)
        if ty.unsolved_vars and not allow_free_vars:
            raise GuppyError(TypeInferenceError(node, ty))
        return with_type(ty, node), ty

    def _check(
        self, expr: ast.expr, ty: Type, kind: str = "expression"
    ) -> tuple[ast.expr, Subst]:
        """Checks an expression against a given type"""
        return ExprChecker(self.ctx).check(expr, ty, kind)

    def visit_Constant(self, node: ast.Constant) -> tuple[ast.expr, Type]:
        ty = python_value_to_guppy_type(node.value, node, self.ctx.globals)
        if ty is None:
            raise GuppyError(IllegalConstant(node, type(node.value)))
        return node, ty

    def _check_generic_param(self, name: str, node: ast.expr) -> tuple[ast.expr, Type]:
        """Helper method to check a generic parameter (ConstParam or TypeParam)."""
        param = self.ctx.generic_params[name]
        match param:
            case ConstParam() as param:
                ast_node = with_loc(node, GenericParamValue(id=name, param=param))
                return ast_node, param.ty
            case TypeParam() as param:
                raise GuppyError(
                    ExpectedError(node, "a value", got=f"type `{param.name}`")
                )
            case _:
                return assert_never(param)

    def visit_Name(self, node: ast.Name) -> tuple[ast.expr, Type]:
        x = node.id
        if x in self.ctx.locals:
            var = self.ctx.locals[x]
            return with_loc(node, PlaceNode(place=var)), var.ty
        elif x in self.ctx.generic_params:
            return self._check_generic_param(x, node)
        elif x in self.ctx.globals:
            match self.ctx.globals[x]:
                case Definition() as defn:
                    return self._check_global(defn, x, node)
                case PythonObject():
                    from guppylang_internals.checker.cfg_checker import (
                        VarNotDefinedError,
                    )

                    # TODO: Emit a hint that the variable could be accessed through a
                    #  comptime expression
                    raise GuppyError(VarNotDefinedError(node, node.id))

        raise InternalGuppyError(
            f"Variable `{x}` is not defined in `TypeSynthesiser`. This should have "
            "been caught by program analysis!"
        )

    def _check_global(
        self, defn: Definition, name: str, node: ast.expr
    ) -> tuple[ast.expr, Type]:
        """Checks a global definition in an expression position."""
        match defn:
            case ValueDef() as defn:
                return with_loc(node, GlobalName(id=name, def_id=defn.id)), defn.ty
            # For types, we return their `__new__` constructor
            case TypeDef() as defn if constr := self.ctx.globals.get_instance_func(
                defn, "__new__"
            ):
                return with_loc(node, GlobalName(id=name, def_id=constr.id)), constr.ty
            # Handle parameter definitions (e.g., nat_var) that may be imported
            case ParamDef():
                # Check if this parameter is in our generic_params
                # (e.g., used in type signature)
                if name in self.ctx.generic_params:
                    return self._check_generic_param(name, node)
                # If not in generic_params, it's being used outside its scope
                raise GuppyError(
                    ExpectedError(node, "a value", got=f"{defn.description} `{name}`")
                )
            case defn:
                raise GuppyError(
                    ExpectedError(node, "a value", got=f"{defn.description} `{name}`")
                )

    def visit_Attribute(self, node: ast.Attribute) -> tuple[ast.expr, Type]:
        from guppylang.defs import GuppyDefinition

        from guppylang_internals.engine import ENGINE

        # A `value.attr` attribute access. Unfortunately, the `attr` is just a string,
        # not an AST node, so we have to compute its span by hand. This is fine since
        # linebreaks are not allowed in the identifier following the `.`
        # The only exception are attributes accesses that are generated during
        # desugaring (for example for iterators in `for` loops). Since those just
        # inherit the span of the sugared code, we could have line breaks there.
        # See https://github.com/quantinuum/guppylang/issues/1301
        span = to_span(node)
        if span.start.line == span.end.line:
            attr_span = Span(span.end.shift_left(len(node.attr)), span.end)
        else:
            attr_span = span
        if module := self._is_python_module(node.value):
            if node.attr in module.__dict__:
                val = module.__dict__[node.attr]
                if isinstance(val, GuppyDefinition):
                    defn = ENGINE.get_parsed(val.id)
                    qual_name = f"{module.__name__}.{defn.name}"
                    return self._check_global(defn, qual_name, node)
            raise GuppyError(
                ModuleMemberNotFoundError(attr_span, module.__name__, node.attr)
            )
        node.value, ty = self.synthesize(node.value)
        if isinstance(ty, StructType) and node.attr in ty.field_dict:
            field = ty.field_dict[node.attr]
            expr: ast.expr
            if isinstance(node.value, PlaceNode):
                # Field access on a place is itself a place
                expr = PlaceNode(place=FieldAccess(node.value.place, field, None))
            else:
                # If the struct is not in a place, then there is no way to address the
                # other fields after this one has been projected (e.g. `f().a` makes
                # you loose access to all fields besides `a`).
                expr = FieldAccessAndDrop(value=node.value, struct_ty=ty, field=field)
            return with_loc(node, expr), field.ty
        elif func := self.ctx.globals.get_instance_func(ty, node.attr):
            name = with_type(
                func.ty, with_loc(node, GlobalName(id=func.name, def_id=func.id))
            )
            # Make a closure by partially applying the `self` argument
            # TODO: Try to infer some type args based on `self`
            result_ty = FunctionType(func.ty.inputs[1:], func.ty.output, func.ty.params)
            return with_loc(node, PartialApply(func=name, args=[node.value])), result_ty
        raise GuppyTypeError(AttributeNotFoundError(attr_span, ty, node.attr))

    def _is_python_module(self, node: ast.expr) -> ModuleType | None:
        """Checks whether an AST node corresponds to a Python module in scope."""
        if isinstance(node, ast.Name):
            x = node.id
            globals = self.ctx.globals
            if x in globals.f_locals or x in globals.f_globals:
                val = (
                    globals.f_locals[x]
                    if x in globals.f_locals
                    else globals.f_globals[x]
                )
                if isinstance(val, ModuleType):
                    return val
        return None

    def visit_Tuple(self, node: ast.Tuple) -> tuple[ast.expr, Type]:
        elems = [self.synthesize(elem) for elem in node.elts]

        node.elts = [n for n, _ in elems]
        return node, TupleType([ty for _, ty in elems])

    def visit_List(self, node: ast.List) -> tuple[ast.expr, Type]:
        check_lists_enabled(node)
        if len(node.elts) == 0:
            unsolved_ty = list_type(ExistentialTypeVar.fresh("T", True, True))
            raise GuppyTypeInferenceError(TypeInferenceError(node, unsolved_ty))
        node.elts[0], el_ty = self.synthesize(node.elts[0])
        node.elts[1:] = [self._check(el, el_ty)[0] for el in node.elts[1:]]
        return node, list_type(el_ty)

    def visit_DesugaredListComp(self, node: DesugaredListComp) -> tuple[ast.expr, Type]:
        node.generators, node.elt, elt_ty = synthesize_comprehension(
            node, node.generators, node.elt, self.ctx
        )
        result_ty = list_type(elt_ty)
        return node, result_ty

    def visit_DesugaredGeneratorExpr(
        self, node: DesugaredGeneratorExpr
    ) -> tuple[ast.expr, Type]:
        # This is a generator in an arbitrary expression position. We don't support
        # generators as first-class value yet, so we always error out here. Special
        # cases where generator are allowed need to explicitly check for them (e.g. see
        # the handling of array comprehensions in the compiler for the `array` function)
        raise GuppyError(UnsupportedError(node, "Generator expressions"))

    def visit_UnaryOp(self, node: ast.UnaryOp) -> tuple[ast.expr, Type]:
        # We need to synthesise the argument type, so we can look up dunder methods
        node.operand, op_ty = self.synthesize(node.operand)

        # Special case for the `not` operation since it is not implemented via a dunder
        # method or control-flow
        if isinstance(node.op, ast.Not):
            node.operand, bool_ty = to_bool(node.operand, op_ty, self.ctx)
            return node, bool_ty

        # Check all other unary expressions by calling out to instance dunder methods
        op, display_name = unary_table[node.op.__class__]
        func = self.ctx.globals.get_instance_func(op_ty, op)
        if func is None:
            raise GuppyTypeError(
                UnaryOperatorNotDefinedError(node.operand, op_ty, display_name)
            )
        return func.synthesize_call([node.operand], node, self.ctx)

    def _synthesize_binary(
        self, left_expr: ast.expr, right_expr: ast.expr, op: AstOp, node: ast.expr
    ) -> tuple[ast.expr, Type]:
        """Helper method to compile binary operators by calling out to dunder methods.

        For example, first try calling `__add__` on the left operand. If that fails, try
        `__radd__` on the right operand.
        """
        if op.__class__ not in binary_table:
            raise GuppyTypeError(UnsupportedError(node, "Operator", singular=True))
        lop, rop, display_name = binary_table[op.__class__]
        left_expr, left_ty = self.synthesize(left_expr)
        right_expr, right_ty = self.synthesize(right_expr)

        if func := self.ctx.globals.get_instance_func(left_ty, lop):
            with suppress(GuppyError):
                return func.synthesize_call([left_expr, right_expr], node, self.ctx)

        if func := self.ctx.globals.get_instance_func(right_ty, rop):
            with suppress(GuppyError):
                return func.synthesize_call([right_expr, left_expr], node, self.ctx)

        raise GuppyTypeError(
            # TODO: Is there a way to get the span of the operator?
            BinaryOperatorNotDefinedError(node, left_ty, right_ty, display_name)
        )

    def synthesize_instance_func(
        self,
        node: ast.expr,
        args: list[ast.expr],
        func_name: str,
        description: str,
        exp_sig: FunctionType | None = None,
        give_reason: bool = False,
    ) -> tuple[ast.expr, Type]:
        """Helper method for expressions that are implemented via instance methods.

        Raises a `GuppyTypeError` if the given instance method is not defined. The error
        message can be customised by passing an `err` string and an optional error
        reason can be printed.

        Optionally, the signature of the instance function can also be checked against a
        given expected signature.
        """
        node, ty = self.synthesize(node)
        func = self.ctx.globals.get_instance_func(ty, func_name)
        if func is None:
            err = BadProtocolError(node, ty, description)
            if give_reason and exp_sig is not None:
                err.add_sub_diagnostic(
                    BadProtocolError.MethodMissing(None, func_name, exp_sig)
                )
            raise GuppyTypeError(err)
        if exp_sig and unify(exp_sig, func.ty.unquantified()[0], {}) is None:
            err = BadProtocolError(node, ty, description)
            err.add_sub_diagnostic(
                BadProtocolError.BadSignature(None, ty, func_name, exp_sig, func.ty)
            )
            raise GuppyError(err)
        return func.synthesize_call([node, *args], node, self.ctx)

    def visit_BinOp(self, node: ast.BinOp) -> tuple[ast.expr, Type]:
        return self._synthesize_binary(node.left, node.right, node.op, node)

    def visit_Compare(self, node: ast.Compare) -> tuple[ast.expr, Type]:
        if len(node.comparators) != 1 or len(node.ops) != 1:
            raise InternalGuppyError(
                "BB contains chained comparison. Should have been removed during CFG "
                "construction."
            )
        left_expr, [op], [right_expr] = node.left, node.ops, node.comparators
        return self._synthesize_binary(left_expr, right_expr, op, node)

    def visit_Subscript(self, node: ast.Subscript) -> tuple[ast.expr, Type]:
        node.value, ty = self.synthesize(node.value)
        # Special case for subscripts on functions: Those are type applications
        if isinstance(ty, FunctionType):
            inst = check_type_apply(ty, node, self.ctx)
            return instantiate_poly(node.value, ty, inst), ty.instantiate(inst)
        item_expr, item_ty = self.synthesize(node.slice)
        # Special case for tuples: Index needs to be known statically in order to infer
        # element type of subscript
        if isinstance(ty, TupleType):
            match item_expr:
                case ast.Constant(value=int(idx)):
                    if 0 <= idx < len(ty.element_types):
                        result_ty = ty.element_types[idx]
                        expr: ast.expr
                        if isinstance(node.value, PlaceNode):
                            tuple_place = TupleAccess(
                                node.value.place, result_ty, idx, None
                            )
                            expr = PlaceNode(place=tuple_place)
                        else:
                            expr = TupleAccessAndDrop(node.value, ty, idx)
                        return with_loc(node, expr), result_ty
                    else:
                        raise GuppyError(
                            TupleIndexOutOfBoundsError(
                                item_expr, idx, len(ty.element_types)
                            )
                        )
                case _:
                    raise GuppyTypeError(ExpectedError(item_expr, "an integer literal"))
        # Otherwise, it's a regular __getitem__ subscript
        # Give the item a unique name so we can refer to it later in case we also want
        # to compile a call to `__setitem__`
        item = Variable(next(tmp_vars), item_ty, item_expr)
        item_node = with_type(item_ty, with_loc(item_expr, PlaceNode(place=item)))
        # Check a call to the `__getitem__` instance function
        exp_sig = FunctionType(
            [
                FuncInput(ty, InputFlags.Inout),
                FuncInput(
                    ExistentialTypeVar.fresh("Key", True, True), InputFlags.NoFlags
                ),
            ],
            ExistentialTypeVar.fresh("Val", True, True),
        )
        getitem_expr, result_ty = self.synthesize_instance_func(
            node.value, [item_node], "__getitem__", "subscriptable", exp_sig
        )
        # Subscripting a place is itself a place
        if isinstance(node.value, PlaceNode):
            place = SubscriptAccess(
                node.value.place, item, result_ty, item_expr, getitem_expr
            )
            expr = PlaceNode(place=place)
        else:
            # If the subscript is not on a place, then there is no way to address the
            # other indices after this one has been projected out (e.g. `f()[0]` makes
            # you loose access to all elements besides 0).
            expr = SubscriptAccessAndDrop(
                item=item,
                item_expr=item_expr,
                getitem_expr=getitem_expr,
                original_expr=node,
            )
        return with_loc(node, expr), result_ty

    def visit_Call(self, node: ast.Call) -> tuple[ast.expr, Type]:
        if len(node.keywords) > 0:
            raise GuppyError(UnsupportedError(node.keywords[0], "Keyword arguments"))
        node.func, ty = self.synthesize(node.func)

        # First handle direct calls of user-defined functions and extension functions
        if isinstance(node.func, GlobalName):
            defn = self.ctx.globals[node.func.def_id]
            if isinstance(defn, CallableDef):
                return defn.synthesize_call(node.args, node, self.ctx)

        # When calling a `PartialApply` node, we just move the args into this call
        if isinstance(node.func, PartialApply):
            node.args = [*node.func.args, *node.args]
            node.func = node.func.func
            return self.visit_Call(node)

        # Otherwise, it must be a function as a higher-order value, or a tensor
        if isinstance(ty, FunctionType):
            args, return_ty, inst = synthesize_call(ty, node.args, node, self.ctx)
            node.func = instantiate_poly(node.func, ty, inst)
            return with_loc(node, LocalCall(func=node.func, args=args)), return_ty
        elif isinstance(ty, TupleType) and (
            function_elems := parse_function_tensor(ty)
        ):
            check_function_tensors_enabled(node.func)
            if any(f.parametrized for f in function_elems):
                raise GuppyError(
                    UnsupportedError(node.func, "Polymorphic function tensors")
                )

            tensor_ty = function_tensor_signature(function_elems)
            args, return_ty, inst = synthesize_call(
                tensor_ty, node.args, node, self.ctx
            )
            assert len(inst) == 0

            return with_loc(
                node, TensorCall(func=node.func, args=args, tensor_ty=tensor_ty)
            ), return_ty

        elif f := self.ctx.globals.get_instance_func(ty, "__call__"):
            return f.synthesize_call(node.args, node, self.ctx)
        else:
            raise GuppyTypeError(NotCallableError(node.func, ty))

    def visit_MakeIter(self, node: MakeIter) -> tuple[ast.expr, Type]:
        node.value, ty = self.synthesize(node.value)
        flags = InputFlags.Owned if not ty.copyable else InputFlags.NoFlags
        exp_sig = FunctionType(
            [FuncInput(ty, flags)], ExistentialTypeVar.fresh("Iter", True, True)
        )
        expr, ty = self.synthesize_instance_func(
            node.value, [], "__iter__", "iterable", exp_sig, True
        )
        # Unwrap the size hint if present
        if is_sized_iter_type(ty) and node.unwrap_size_hint:
            expr, ty = self.synthesize_instance_func(expr, [], "unwrap_iter", "")

        # If the iterator was created by a `for` loop, we can add some extra checks to
        # produce nicer errors for linearity violations. Namely, `break` and `return`
        # are not allowed when looping over a non-copyable iterator (`continue` is
        # allowed)
        if not ty.droppable and isinstance(node.origin_node, ast.For):
            breaks = breaks_in_loop(node.origin_node) or return_nodes_in_ast(
                node.origin_node
            )
            if breaks:
                err = NonDroppableForBreakError(breaks[0])
                err.add_sub_diagnostic(
                    NonDroppableForBreakError.NonDroppableIteratorType(node, ty)
                )
                raise GuppyTypeError(err)
        return expr, ty

    def visit_IterNext(self, node: IterNext) -> tuple[ast.expr, Type]:
        node.value, ty = self.synthesize(node.value)
        flags = InputFlags.Owned if not ty.copyable else InputFlags.NoFlags
        exp_sig = FunctionType(
            [FuncInput(ty, flags)],
            option_type(TupleType([ExistentialTypeVar.fresh("T", True, True), ty])),
        )
        return self.synthesize_instance_func(
            node.value, [], "__next__", "an iterator", exp_sig, True
        )

    def visit_ListComp(self, node: ast.ListComp) -> tuple[ast.expr, Type]:
        raise InternalGuppyError(
            "BB contains `ListComp`. Should have been removed during CFG"
            f"construction: `{ast.unparse(node)}`"
        )

    def visit_ComptimeExpr(self, node: ComptimeExpr) -> tuple[ast.expr, Type]:
        python_val = eval_comptime_expr(node, self.ctx)
        if ty := python_value_to_guppy_type(python_val, node, self.ctx.globals):
            return with_loc(node, ast.Constant(value=python_val)), ty

        raise GuppyError(IllegalComptimeExpressionError(node.value, type(python_val)))

    def visit_NamedExpr(self, node: ast.NamedExpr) -> tuple[ast.expr, Type]:
        raise InternalGuppyError(
            "BB contains `NamedExpr`. Should have been removed during CFG"
            f"construction: `{ast.unparse(node)}`"
        )

    def visit_BoolOp(self, node: ast.BoolOp) -> tuple[ast.expr, Type]:
        raise InternalGuppyError(
            "BB contains `BoolOp`. Should have been removed during CFG construction: "
            f"`{ast.unparse(node)}`"
        )

    def visit_IfExp(self, node: ast.IfExp) -> tuple[ast.expr, Type]:
        raise InternalGuppyError(
            "BB contains `IfExp`. Should have been removed during CFG construction: "
            f"`{ast.unparse(node)}`"
        )

    def generic_visit(self, node: ast.expr) -> NoReturn:
        """Called if no explicit visitor function exists for a node."""
        raise GuppyError(UnsupportedError(node, "This expression", singular=True))


def check_type_against(
    act: Type, exp: Type, node: ast.expr, ctx: Context, kind: str = "expression"
) -> tuple[ast.expr, Subst, Inst]:
    """Checks a type against another type.

    Returns a substitution for the free variables the expected type and an instantiation
    for the parameters in the actual type. Note that the expected type may not be
    parametrised and the actual type may not contain free unification variables.
    """
    assert not isinstance(exp, FunctionType) or not exp.parametrized
    assert not act.unsolved_vars

    # The actual type may be parametrised. In that case, we have to find an
    # instantiation to avoid higher-rank types.
    subst: Subst | None
    if isinstance(act, FunctionType) and act.parametrized:
        unquantified, free_vars = act.unquantified()
        subst = unify(exp, unquantified, {})
        if subst is None:
            raise GuppyTypeError(TypeMismatchError(node, exp, act, kind))
        # Check that we have found a valid instantiation for all params
        for i, v in enumerate(free_vars):
            param = act.params[i].name
            if v not in subst:
                err = TypeMismatchError(node, exp, act, kind)
                err.add_sub_diagnostic(TypeMismatchError.CantInferParam(None, param))
                raise GuppyTypeInferenceError(err)
            if subst[v].unsolved_vars:
                err = TypeMismatchError(node, exp, act, kind)
                err.add_sub_diagnostic(
                    TypeMismatchError.CantInstantiateFreeVars(None, param, subst[v])
                )
                raise GuppyTypeError(err)
        inst = [subst[v].to_arg() for v in free_vars]
        subst = {v: t for v, t in subst.items() if v in exp.unsolved_vars}

        # Finally, check that the instantiation respects the linearity requirements
        check_inst(act, inst, node)

        return node, subst, inst

    # Otherwise, we know that `act` has no unsolved type vars, so unification is trivial
    assert not act.unsolved_vars
    subst = unify(exp, act, {})
    if subst is None:
        # Maybe we can implicitly coerce `act` to `exp`
        if coerced := try_coerce_to(act, exp, node, ctx):
            return coerced, {}, []
        raise GuppyTypeError(TypeMismatchError(node, exp, act, kind))
    return node, subst, []


def try_coerce_to(
    act: Type, exp: Type, node: ast.expr, ctx: Context
) -> ast.expr | None:
    """Tries to implicitly coerce an expression to a different type.

    Returns the coerced expression or `None` if the type cannot be implicitly coerced.
    """
    # Currently, we only support implicit coercions of numeric types
    if not isinstance(act, NumericType) or not isinstance(exp, NumericType):
        return None
    # Ordering on `NumericType.Kind` defines the coercion relation
    if act.kind < exp.kind:
        f = ctx.globals.get_instance_func(act, f"__{exp.kind.name.lower()}__")
        assert f is not None
        node, subst = f.check_call([node], exp, node, ctx)
        assert len(subst) == 0, "Coercion methods are not generic"
        return node
    return None


def check_type_apply(ty: FunctionType, node: ast.Subscript, ctx: Context) -> Inst:
    """Checks a `f[T1, T2, ...]` type application of a generic function."""
    func = node.value
    arg_exprs = (
        node.slice.elts
        if isinstance(node.slice, ast.Tuple) and len(node.slice.elts) > 0
        else [node.slice]
    )
    globals = ctx.globals

    if not ty.parametrized:
        func_name = globals[func.def_id].name if isinstance(func, GlobalName) else None
        raise GuppyError(TypeApplyNotGenericError(node, func_name))

    exp, act = len(ty.params), len(arg_exprs)
    assert exp > 0
    assert act > 0
    if exp != act:
        if exp < act:
            span = Span(to_span(arg_exprs[exp]).start, to_span(arg_exprs[-1]).end)
        else:
            span = Span(to_span(arg_exprs[-1]).end, to_span(node).end)
        err = WrongNumberOfArgsError(span, exp, act, detailed=True, is_type_apply=True)
        err.add_sub_diagnostic(WrongNumberOfArgsError.SignatureHint(None, ty))
        raise GuppyError(err)

    inst = [arg_from_ast(node, ctx.parsing_ctx) for node in arg_exprs]
    check_all_args(ty.params, inst, "", node, arg_exprs)
    return inst


def check_num_args(
    exp: int, act: int, node: AstNode, sig: FunctionType | None = None
) -> None:
    """Checks that the correct number of arguments have been passed to a function."""
    if exp == act:
        return
    span, detailed = to_span(node), False
    if isinstance(node, ast.Call):
        # We can construct a nicer error span if we know it's a regular call
        detailed = True
        if exp < act:
            span = Span(to_span(node.args[exp]).start, to_span(node.args[-1]).end)
        elif act > 0:
            span = Span(to_span(node.args[-1]).end, to_span(node).end)
        else:
            span = Span(to_span(node.func).end, to_span(node).end)
    err = WrongNumberOfArgsError(span, exp, act, detailed)
    if sig:
        err.add_sub_diagnostic(WrongNumberOfArgsError.SignatureHint(None, sig))
    raise GuppyTypeError(err)


def type_check_args(
    inputs: list[ast.expr],
    func_ty: FunctionType,
    subst: Subst,
    ctx: Context,
    node: AstNode,
) -> tuple[list[ast.expr], Subst]:
    """Checks the arguments of a function call and infers free type variables.

    We expect that parameters have been replaced with free unification variables.
    Checks that all unification variables can be inferred.
    """
    assert not func_ty.parametrized
    check_num_args(len(func_ty.inputs), len(inputs), node, func_ty)

    new_args: list[ast.expr] = []
    comptime_args = iter(func_ty.comptime_args)
    for inp, func_inp in zip(inputs, func_ty.inputs, strict=True):
        a, s = ExprChecker(ctx).check(inp, func_inp.ty.substitute(subst), "argument")
        subst |= s
        if InputFlags.Inout in func_inp.flags and isinstance(a, PlaceNode):
            a.place = check_place_assignable(
                a.place, ctx, a, "able to borrow subscripted elements"
            )
        if InputFlags.Comptime in func_inp.flags:
            comptime_arg = next(comptime_args)
            const = comptime_arg.const.substitute(subst)
            s = check_comptime_arg(a, const, func_inp.ty.substitute(subst), subst)
            subst |= s
        new_args.append(a)
    assert next(comptime_args, None) is None

    # Check whether we have found instantiations for all unification variables occurring
    # in the input types
    for inp in func_ty.inputs:
        if not set.issubset(inp.ty.unsolved_vars, subst.keys()):
            raise GuppyTypeInferenceError(
                TypeInferenceError(node, inp.ty.substitute(subst))
            )

    # We also have to check that we found instantiations for all vars in the return type
    if not set.issubset(func_ty.output.unsolved_vars, subst.keys()):
        raise GuppyTypeInferenceError(
            TypeInferenceError(node, func_ty.output.substitute(subst))
        )

    return new_args, subst


def check_place_assignable(
    place: Place, ctx: Context, node: ast.expr, reason: str
) -> Place:
    """Performs additional checks for assignments to places, for example for borrowed
    place arguments after function returns.

    In particular, we need to check that places involving `place[item]` subscripts
    implement the corresponding `__setitem__` method.
    """
    match place:
        case Variable():
            return place
        case FieldAccess(parent=parent):
            return replace(
                place, parent=check_place_assignable(parent, ctx, node, reason)
            )
        case SubscriptAccess(parent=parent, item=item, ty=ty):
            # Create temporary variable for the setitem value
            tmp_var = Variable(next(tmp_vars), item.ty, node)
            # Check a call to the `__setitem__` instance function
            exp_sig = FunctionType(
                [
                    FuncInput(parent.ty, InputFlags.Inout),
                    FuncInput(
                        # Due to potential coercions that were applied during the
                        # `__getitem__` call (e.g. coercing a nat index to int), we're
                        # not allowed to rely on `item.ty` here.
                        # See https://github.com/CQCL/guppylang/issues/1356
                        ExistentialTypeVar.fresh("T", True, True),
                        InputFlags.NoFlags,
                    ),
                    FuncInput(ty, InputFlags.Owned),
                ],
                NoneType(),
            )
            setitem_args: list[ast.expr] = [
                with_type(parent.ty, with_loc(node, PlaceNode(parent))),
                with_type(item.ty, with_loc(node, PlaceNode(item))),
                with_type(ty, with_loc(node, PlaceNode(tmp_var))),
            ]
            setitem_call, _ = ExprSynthesizer(ctx).synthesize_instance_func(
                setitem_args[0],
                setitem_args[1:],
                "__setitem__",
                reason,
                exp_sig,
                True,
            )
            return replace(place, setitem_call=SetitemCall(setitem_call, tmp_var))
        case TupleAccess(parent=parent):
            return replace(
                place, parent=check_place_assignable(parent, ctx, node, reason)
            )


def check_comptime_arg(
    arg: ast.expr, exp_const: Const, ty: Type, subst: Subst | None
) -> Subst:
    """Checks that an expression can be passes as a valid `@comptime` argument.

    Also checks that the value matches the provided constant. Returns a substitution
    that solves any existential variables occurring in provided constant.
    """
    const: Const
    match arg:
        case ast.Constant(value=v):
            const = ConstValue(ty, v)
        case PlaceNode(place=ComptimeVariable(ty=ty, static_value=v)):
            const = ConstValue(ty, v)
        case GenericParamValue(param=const_param):
            const = const_param.to_bound().const
        case arg:
            # Anything else is considered unknown at comptime, but we can give some
            # nicer error hints by inspecting in more detail
            err = ComptimeUnknownError(arg, "argument")
            s: SubDiagnostic
            match arg:
                case PlaceNode(place=place) if place.root.is_func_input:
                    s = ComptimeUnknownError.InputHint(place.defined_at, place)
                case PlaceNode(place=place) if not is_tmp_var(place.root.name):
                    s = ComptimeUnknownError.VariableHint(place.defined_at, place)
                case arg:
                    s = ComptimeUnknownError.FallbackHint(arg)
            err.add_sub_diagnostic(s)
            err.add_sub_diagnostic(ComptimeUnknownError.Feedback(None))
            raise GuppyError(err)
    # Unify with expected constant to check and maybe infer some variables
    subst = unify(exp_const, const, subst)
    if subst is None:
        raise GuppyError(ConstMismatchError(arg, exp_const, const))
    return subst


def synthesize_call(
    func_ty: FunctionType, args: list[ast.expr], node: AstNode, ctx: Context
) -> tuple[list[ast.expr], Type, Inst]:
    """Synthesizes the return type of a function call.

    Returns an annotated argument list, the synthesized return type, and an
    instantiation for the quantifiers in the function type.
    """
    assert not func_ty.unsolved_vars
    check_num_args(len(func_ty.inputs), len(args), node, func_ty)

    # Replace quantified variables with free unification variables and try to infer an
    # instantiation by checking the arguments
    unquantified, free_vars = func_ty.unquantified()
    args, subst = type_check_args(args, unquantified, {}, ctx, node)

    # Success implies that the substitution is closed
    assert all(not t.unsolved_vars for t in subst.values())
    inst = check_all_solved(subst, free_vars, func_ty, node)

    # Finally, check that the instantiation respects the linearity requirements
    check_inst(func_ty, inst, node)

    return args, unquantified.output.substitute(subst), inst


def check_call(
    func_ty: FunctionType,
    inputs: list[ast.expr],
    ty: Type,
    node: AstNode,
    ctx: Context,
    kind: str = "expression",
) -> tuple[list[ast.expr], Subst, Inst]:
    """Checks the return type of a function call against a given type.

    Returns an annotated argument list, a substitution for the free variables in the
    expected type, and an instantiation for the quantifiers in the function type.
    """
    assert not func_ty.unsolved_vars
    check_num_args(len(func_ty.inputs), len(inputs), node, func_ty)

    # When checking, we can use the information from the expected return type to infer
    # some type arguments. However, this pushes errors inwards. For example, given a
    # function `foo: forall T. T -> T`, the following type mismatch would be reported:
    #
    #       x: int = foo(None)
    #                    ^^^^  Expected argument of type `int`, got `None`
    #
    # But the following error location would be more intuitive for users:
    #
    #       x: int = foo(None)
    #                ^^^^^^^^^  Expected expression of type `int`, got `None`
    #
    # In other words, if we can get away with synthesising the call without the extra
    # information from the expected type, we should do that to improve the error.

    # TODO: The approach below can result in exponential runtime in the worst case.
    #  However the bad case, e.g. `x: int = foo(foo(...foo(?)...))`, shouldn't be common
    #  in practice. Can we do better than that?

    # synthesize_call may modify args and node in place,
    # hence we deepcopy them before passing in the function
    node_copy = copy.deepcopy(node)
    inputs_copy = copy.deepcopy(inputs)

    try:
        inputs, synth, inst = synthesize_call(func_ty, inputs, node, ctx)
        subst = unify(ty, synth, {})
        if subst is None:
            raise GuppyTypeError(TypeMismatchError(node, ty, synth, kind))
        else:
            return inputs, subst, inst
    except GuppyTypeInferenceError:
        pass

    # Restore the state of these values from before they were potentially
    # modified by `synthesize_call`.
    inputs = inputs_copy
    node = node_copy

    # If synthesis fails, we try again, this time also using information from the
    # expected return type
    unquantified, free_vars = func_ty.unquantified()
    subst = unify(ty, unquantified.output, {})
    if subst is None:
        raise GuppyTypeError(TypeMismatchError(node, ty, unquantified.output, kind))

    # Try to infer more by checking against the arguments
    inputs, subst = type_check_args(inputs, unquantified, subst, ctx, node)

    # Also make sure we found an instantiation for all free vars in the type we're
    # checking against
    if not set.issubset(ty.unsolved_vars, subst.keys()):
        unsolved = (subst.keys() - ty.unsolved_vars).pop()
        err = TypeMismatchError(node, ty, func_ty.output.substitute(subst))
        err.add_sub_diagnostic(
            TypeMismatchError.CantInferParam(None, unsolved.display_name)
        )
        raise GuppyTypeInferenceError(err)

    # Success implies that the substitution is closed
    assert all(not t.unsolved_vars for t in subst.values())
    inst = check_all_solved(subst, free_vars, func_ty, node)
    subst = {v: t for v, t in subst.items() if v in ty.unsolved_vars}

    # Finally, check that the instantiation respects the linearity requirements
    check_inst(func_ty, inst, node)

    return inputs, subst, inst


def check_all_solved(
    subst: Subst,
    free_vars: Sequence[ExistentialVar],
    func_ty: FunctionType,
    loc: AstNode,
) -> Inst:
    """Checks that a substitution solves all parameters of a function.

    Using 3.12 generic syntax, users can declare parameters that don't occur in the
    signature. Those will remain unsolved, even after unifying all function arguments,
    so we have to perform this extra check.

    Returns an instantiation of all free variables, or emits a user error if some are
    not solved.
    """
    for v in free_vars:
        if v not in subst:
            err = ParameterInferenceError(loc, v.display_name)
            err.add_sub_diagnostic(ParameterInferenceError.SignatureHint(None, func_ty))
            raise GuppyTypeInferenceError(err)
    return [subst[v].to_arg() for v in free_vars]


def check_inst(func_ty: FunctionType, inst: Inst, node: AstNode) -> None:
    """Checks if an instantiation is valid.

    Makes sure that the linearity requirements are satisfied.
    """
    for param, arg in zip(func_ty.params, inst, strict=True):
        param = param.instantiate_bounds(inst)

        # Give a more informative error message for linearity issues
        if isinstance(param, TypeParam) and isinstance(arg, TypeArg):
            if param.must_be_copyable and not arg.ty.copyable:
                raise GuppyTypeError(
                    NonLinearInstantiateError(node, param, func_ty, arg.ty)
                )
            if param.must_be_droppable and not arg.ty.droppable:
                raise GuppyTypeError(
                    NonLinearInstantiateError(node, param, func_ty, arg.ty)
                )
        # For everything else, we fall back to the default checking implementation
        param.check_arg(arg, node)


def instantiate_poly(node: ast.expr, ty: FunctionType, inst: Inst) -> ast.expr:
    """Instantiates quantified type arguments in a function."""
    assert len(ty.params) == len(inst)
    if len(inst) > 0:
        # Partial applications need to be instantiated on the inside
        if isinstance(node, PartialApply):
            full_ty = get_type(node.func)
            assert isinstance(full_ty, FunctionType)
            assert full_ty.params == ty.params
            node.func = instantiate_poly(node.func, full_ty, inst)
        else:
            node = with_loc(node, TypeApply(with_type(ty, node), inst))
        return with_type(ty.instantiate(inst), node)
    return with_type(ty, node)


def to_bool(node: ast.expr, node_ty: Type, ctx: Context) -> tuple[ast.expr, Type]:
    """Tries to turn a node into a bool"""
    if is_bool_type(node_ty):
        return node, node_ty
    synth = ExprSynthesizer(ctx)
    exp_sig = FunctionType([FuncInput(node_ty, InputFlags.Inout)], bool_type())
    return synth.synthesize_instance_func(node, [], "__bool__", "truthy", exp_sig, True)


def synthesize_comprehension(
    node: AstNode, gens: list[DesugaredGenerator], elt: ast.expr, ctx: Context
) -> tuple[list[DesugaredGenerator], ast.expr, Type]:
    """Helper function to synthesise the element type of a list comprehension."""
    # If there are no more generators left, we can check the list element
    if not gens:
        elt, elt_ty = ExprSynthesizer(ctx).synthesize(elt)
        return gens, elt, elt_ty

    # Check the first generator
    gen, *gens = gens
    gen, inner_ctx = check_generator(gen, ctx)

    # Check remaining generators in inner context
    gens, elt, elt_ty = synthesize_comprehension(node, gens, elt, inner_ctx)

    return [gen, *gens], elt, elt_ty


def check_generator(
    gen: DesugaredGenerator, ctx: Context
) -> tuple[DesugaredGenerator, Context]:
    """Helper function to check a single generator.

    Returns the type annotated generator together with a new nested context in which the
    generator variables are bound.
    """
    from guppylang_internals.checker.stmt_checker import StmtChecker

    # Check the iterator in the outer context
    gen.iter_assign = StmtChecker(ctx).visit_Assign(gen.iter_assign)

    # The rest is checked in a new nested context to ensure that variables don't escape
    # their scope
    inner_locals: Locals[str, Variable] = Locals({}, parent_scope=ctx.locals)
    inner_ctx = Context(ctx.globals, inner_locals, ctx.generic_params)
    expr_sth, stmt_chk = ExprSynthesizer(inner_ctx), StmtChecker(inner_ctx)
    gen.iter, iter_ty = expr_sth.visit(gen.iter)
    gen.iter = with_type(iter_ty, gen.iter)

    # The type returned by `next_call` is `Option[tuple[elt_ty, iter_ty]]`
    gen.next_call, option_ty = expr_sth.synthesize(gen.next_call)
    next_ty = get_element_type(option_ty)
    assert isinstance(next_ty, TupleType)
    [elt_ty, _] = next_ty.element_types
    gen.target = stmt_chk._check_assign(gen.target, gen.next_call, elt_ty)

    # Check `if` guards
    for i in range(len(gen.ifs)):
        gen.ifs[i], if_ty = expr_sth.synthesize(gen.ifs[i])
        gen.ifs[i], _ = to_bool(gen.ifs[i], if_ty, inner_ctx)

    return gen, inner_ctx


def eval_comptime_expr(node: ComptimeExpr, ctx: Context) -> Any:
    """Evaluates a `comptime(...)` expression."""
    # The method we used for obtaining the Python variables in scope only works in
    # CPython (see `get_py_scope()`).
    if sys.implementation.name != "cpython":
        raise GuppyError(ComptimeExprNotCPythonError(node))

    try:
        python_val = eval(ast.unparse(node.value), DummyEvalDict(ctx, node.value))  # noqa: S307
    except DummyEvalDict.GuppyVarUsedError as e:
        raise GuppyError(ComptimeExprNotStaticError(e.node or node, e.var)) from None
    except Exception as e:
        # Remove the top frame pointing to the `eval` call from the stack trace
        tb = e.__traceback__.tb_next if e.__traceback__ else None
        tb_formatted = "".join(traceback.format_exception(type(e), e, tb))
        raise GuppyError(ComptimeExprEvalError(node.value, tb_formatted)) from e
    return python_val


def python_value_to_guppy_type(
    v: Any, node: ast.AST, globals: Globals, type_hint: Type | None = None
) -> Type | None:
    """Turns a primitive Python value into a Guppy type.

    Accepts an optional `type_hint` for the expected expression type that is used to
    infer a more precise type (e.g. distinguishing between `int` and `nat`). Note that
    invalid hints are ignored, i.e. no user error are emitted.

    Returns `None` if the Python value cannot be represented in Guppy.
    """
    match v:
        case bool():
            return bool_type()
        case str():
            return string_type()
        # Only resolve `int` to `nat` if the user specifically asked for it
        case int(n) if type_hint == nat_type() and n >= 0:
            _int_bounds_check(n, node, signed=False)
            return nat_type()
        # Otherwise, default to `int` for consistency with Python
        case int(n):
            _int_bounds_check(n, node, signed=True)
            return int_type()
        case float():
            return float_type()
        case tuple(elts):
            hints = (
                type_hint.element_types
                if isinstance(type_hint, TupleType)
                else len(elts) * [None]
            )
            tys = [
                python_value_to_guppy_type(elt, node, globals, hint)
                for elt, hint in zip(elts, hints, strict=False)
            ]
            if any(ty is None for ty in tys):
                return None
            return TupleType(cast("list[Type]", tys))
        case list():
            return _python_list_to_guppy_type(v, node, globals, type_hint)
        case None:
            return NoneType()
        case _:
            return None


def _int_bounds_check(value: int, node: AstNode, signed: bool) -> None:
    bit_width = 1 << NumericType.INT_WIDTH
    if signed:
        max_v = (1 << (bit_width - 1)) - 1
        min_v = -(1 << (bit_width - 1))
    else:
        max_v = (1 << bit_width) - 1
        min_v = 0
    if value < min_v or value > max_v:
        err = IntOverflowError(node, signed, bit_width, value < min_v)
        raise GuppyTypeError(err)


def _python_list_to_guppy_type(
    vs: list[Any], node: ast.AST, globals: Globals, type_hint: Type | None
) -> OpaqueType | None:
    """Turns a Python list into a Guppy type.

    Returns `None` if the list contains different types or types that are not
    representable in Guppy.
    """
    if len(vs) == 0:
        return frozenarray_type(ExistentialTypeVar.fresh("T", True, True), 0)

    # All the list elements must have a unifiable types
    v, *rest = vs
    elt_hint = (
        get_element_type(type_hint)
        if type_hint and is_frozenarray_type(type_hint)
        else None
    )
    el_ty = python_value_to_guppy_type(v, node, globals, elt_hint)
    if el_ty is None:
        return None
    for v in rest:
        ty = python_value_to_guppy_type(v, node, globals, elt_hint)
        if ty is None:
            return None
        if (subst := unify(ty, el_ty, {})) is None:
            raise GuppyError(ComptimeExprIncoherentListError(node))
        el_ty = el_ty.substitute(subst)
    return frozenarray_type(el_ty, len(vs))
