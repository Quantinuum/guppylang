import ast
from dataclasses import dataclass
from typing import ClassVar

from typing_extensions import assert_never

from guppylang_internals.ast_util import get_type, with_loc, with_type
from guppylang_internals.checker.core import Context
from guppylang_internals.checker.errors.generic import UnsupportedError
from guppylang_internals.checker.errors.type_errors import (
    ArrayComprUnknownSizeError,
    TypeMismatchError,
)
from guppylang_internals.checker.expr_checker import (
    ExprChecker,
    ExprSynthesizer,
    check_call,
    check_num_args,
    check_type_against,
    synthesize_call,
    synthesize_comprehension,
)
from guppylang_internals.definition.custom import (
    CustomCallChecker,
)
from guppylang_internals.diagnostic import Error, Note
from guppylang_internals.error import GuppyError, GuppyTypeError, InternalGuppyError
from guppylang_internals.nodes import (
    BarrierExpr,
    DesugaredArrayComp,
    DesugaredGeneratorExpr,
    ExitKind,
    GlobalCall,
    MakeIter,
    PanicExpr,
)
from guppylang_internals.tys.arg import ConstArg, TypeArg
from guppylang_internals.tys.builtin import (
    array_type,
    array_type_def,
    bool_type,
    get_element_type,
    get_iter_size,
    int_type,
    is_array_type,
    is_sized_iter_type,
    nat_type,
    sized_iter_type,
    string_type,
)
from guppylang_internals.tys.const import Const, ConstValue
from guppylang_internals.tys.subst import Subst
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    Type,
    unify,
)


class ReversingChecker(CustomCallChecker):
    """Call checker for reverse arithmetic methods.

    For examples, turns a call to `__radd__` into a call to `__add__` with reversed
    arguments.
    """

    def parse_name(self) -> str:
        # Must be a dunder method
        assert self.func.name.startswith("__")
        assert self.func.name.endswith("__")
        name = self.func.name[2:-2]
        # Remove the `r`
        assert name.startswith("r")
        return f"__{name[1:]}__"

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        [self_arg, other_arg] = args
        self_arg, self_ty = ExprSynthesizer(self.ctx).synthesize(self_arg)
        f = self.ctx.globals.get_instance_func(self_ty, self.parse_name())
        assert f is not None
        return f.synthesize_call([other_arg, self_arg], self.node, self.ctx)


class UnsupportedChecker(CustomCallChecker):
    """Call checker for Python builtin functions that are not available in Guppy.

    Gives the uses a nicer error message when they try to use an unsupported feature.
    """

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        err = UnsupportedError(
            self.node, f"Builtin method `{self.func.name}`", singular=True
        )
        raise GuppyError(err)

    def check(self, args: list[ast.expr], ty: Type) -> tuple[ast.expr, Subst]:
        err = UnsupportedError(
            self.node, f"Builtin method `{self.func.name}`", singular=True
        )
        raise GuppyError(err)


class DunderChecker(CustomCallChecker):
    """Call checker for builtin functions that call out to dunder instance methods"""

    dunder_name: str
    num_args: int

    def __init__(self, dunder_name: str, num_args: int = 1):
        assert num_args > 0
        self.dunder_name = dunder_name
        self.num_args = num_args

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        check_num_args(self.num_args, len(args), self.node)
        fst, *rest = args
        return ExprSynthesizer(self.ctx).synthesize_instance_func(
            fst,
            rest,
            self.dunder_name,
            f"a valid argument to `{self.func.name}`",
            give_reason=True,
        )


class CallableChecker(CustomCallChecker):
    """Call checker for the builtin `callable` function"""

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        check_num_args(1, len(args), self.node)
        [arg] = args
        arg, ty = ExprSynthesizer(self.ctx).synthesize(arg)
        is_callable = (
            isinstance(ty, FunctionType)
            or self.ctx.globals.get_instance_func(ty, "__call__") is not None
        )
        const = with_loc(self.node, ast.Constant(value=is_callable))
        return const, bool_type()


class ArrayCopyChecker(CustomCallChecker):
    """Function call checker for the `array.copy` function."""

    @dataclass(frozen=True)
    class NonCopyableElementsError(Error):
        title: ClassVar[str] = "Non-copyable elements"
        span_label: ClassVar[str] = "Elements of type `{ty}` cannot be copied."
        ty: Type

        @dataclass(frozen=True)
        class Explanation(Note):
            message: ClassVar[str] = "Only arrays with copyable elements can be copied"

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        # First, check if we're trying to copy a non-copyable element type to give a
        # nicer error message. Then, do the full `synthesize_call` type check
        if len(args) == 1:
            args[0], array_ty = ExprSynthesizer(self.ctx).synthesize(args[0])
            if is_array_type(array_ty):
                elem_ty = get_element_type(array_ty)
                if not elem_ty.copyable:
                    err = ArrayCopyChecker.NonCopyableElementsError(self.node, elem_ty)
                    err.add_sub_diagnostic(
                        ArrayCopyChecker.NonCopyableElementsError.Explanation(None)
                    )
                    raise GuppyTypeError(err)
        [array_arg], _, inst = synthesize_call(self.func.ty, args, self.node, self.ctx)
        node = GlobalCall(def_id=self.func.id, args=[array_arg], type_args=inst)
        return with_loc(self.node, node), get_type(array_arg)


class ArrayIndexChecker(CustomCallChecker):
    """Custom call checker that performs compile-time bounds
      checking for array indexing.

    When the array size is statically known and the index is a literal constant,
    this checker validates that the index is within bounds and raises an error
    at compile time if it's not.
    """

    @dataclass(frozen=True)
    class IndexOutOfBoundsError(Error):
        title: ClassVar[str] = "Index out of bounds"
        span_label: ClassVar[str] = (
            "Array index {index} is out of bounds for array of size {size}"
        )
        index: int
        size: int

    def _extract_constant_index(self, index_expr: ast.expr) -> int | None:
        """Extract a constant integer value from an index expression if possible.

        Handles both AST constants and PlaceNode structures.
        """
        # Case 1: Simple AST constant (e.g., arr[8] - direct Constant node)
        if isinstance(index_expr, ast.Constant) and isinstance(index_expr.value, int):
            return index_expr.value

        # Case 2: PlaceNode with constant defined_at (e.g., after type checking)
        if hasattr(index_expr, "place"):
            place = index_expr.place
            if hasattr(place, "defined_at"):
                defined_at = place.defined_at
                # Check if defined_at is a Constant node with a value
                if isinstance(defined_at, ast.Constant) and isinstance(
                    defined_at.value, int
                ):
                    return defined_at.value

        return None

    def check(self, args: list[ast.expr], ty: Type) -> tuple[ast.expr, Subst]:
        """Check-mode: verify arguments against
        expected type and perform bounds check."""

        # Run regular type checking for the arguments
        args, subs, type_args = check_call(self.func.ty, args, ty, self.node, self.ctx)

        # Extract the array length from type arguments
        # Type args are: [element_type, length]
        if len(type_args) >= 2:
            length_arg = type_args[1]

            # Check if the array size is statically known
            if hasattr(length_arg, "const") and isinstance(
                length_arg.const, ConstValue
            ):
                array_length = length_arg.const.value

                # The index is the second argument (first is self/array)
                if len(args) >= 2:
                    index_expr = args[1]

                    # Extract constant index value
                    index_value = self._extract_constant_index(index_expr)

                    # Perform bounds check
                    if index_value is not None and (
                        index_value < 0 or index_value >= array_length
                    ):
                        raise GuppyError(
                            ArrayIndexChecker.IndexOutOfBoundsError(
                                self.node,
                                index=index_value,
                                size=array_length,
                            )
                        )

        # Return the synthesized node and type
        node = GlobalCall(def_id=self.func.id, args=args, type_args=type_args)
        return with_loc(self.node, node), subs

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        """Synthesize-mode: infer return type and perform bounds check."""
        # Run regular type synthesis for the arguments
        args, subs, type_args = synthesize_call(self.func.ty, args, self.node, self.ctx)

        # Extract the array length from type arguments
        # Type args are: [element_type, length]
        if len(type_args) >= 2:
            length_arg = type_args[1]

            # Check if the array size is statically known
            if hasattr(length_arg, "const") and isinstance(
                length_arg.const, ConstValue
            ):
                array_length = length_arg.const.value

                # The index is the second argument (first is self/array)
                if len(args) >= 2:
                    index_expr = args[1]

                    # Extract constant index value
                    index_value = self._extract_constant_index(index_expr)

                    # Perform bounds check
                    if index_value is not None and (
                        index_value < 0 or index_value >= array_length
                    ):
                        raise GuppyError(
                            ArrayIndexChecker.IndexOutOfBoundsError(
                                self.node,
                                index=index_value,
                                size=array_length,
                            )
                        )

        # Return the synthesized node and type
        node = GlobalCall(def_id=self.func.id, args=args, type_args=type_args)
        return with_loc(self.node, node), subs


class NewArrayChecker(CustomCallChecker):
    """Function call checker for the `array.__new__` function."""

    @dataclass(frozen=True)
    class InferenceError(Error):
        title: ClassVar[str] = "Cannot infer type"
        span_label: ClassVar[str] = "Cannot infer the type of this array"

        @dataclass(frozen=True)
        class Suggestion(Note):
            message: ClassVar[str] = (
                "Consider adding a type annotation: `x: array[???] = ...`"
            )

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        match args:
            case []:
                err = NewArrayChecker.InferenceError(self.node)
                err.add_sub_diagnostic(NewArrayChecker.InferenceError.Suggestion(None))
                raise GuppyTypeError(err)
            # Either an array comprehension
            case [DesugaredGeneratorExpr() as compr]:
                return self.synthesize_array_comprehension(compr)
            # Or a list of array elements
            case [fst, *rest]:
                fst, ty = ExprSynthesizer(self.ctx).synthesize(fst)
                checker = ExprChecker(self.ctx)
                for i in range(len(rest)):
                    rest[i], subst = checker.check(rest[i], ty)
                    assert len(subst) == 0, "Array element type is closed"
                result_ty = array_type(ty, len(args))
                call = GlobalCall(
                    def_id=self.func.id, args=[fst, *rest], type_args=result_ty.args
                )
                return with_loc(self.node, call), result_ty
            case args:
                return assert_never(args)  # type: ignore[arg-type]

    def check(self, args: list[ast.expr], ty: Type) -> tuple[ast.expr, Subst]:
        if not is_array_type(ty):
            dummy_array_ty = array_type_def.check_instantiate(
                [p.to_existential()[0] for p in array_type_def.params], self.node
            )
            raise GuppyTypeError(TypeMismatchError(self.node, ty, dummy_array_ty))
        subst: Subst = {}
        match ty.args:
            case [TypeArg(ty=elem_ty), ConstArg(length)]:
                match args:
                    # Either an array comprehension
                    case [DesugaredGeneratorExpr() as compr]:
                        # TODO: We could use the type information to infer some stuff
                        #  in the comprehension
                        arr_compr, res_ty = self.synthesize_array_comprehension(compr)
                        arr_compr = with_loc(self.node, arr_compr)
                        arr_compr, subst, _ = check_type_against(
                            res_ty, ty, arr_compr, self.ctx
                        )
                        return arr_compr, subst
                    # Or a list of array elements
                    case args:
                        checker = ExprChecker(self.ctx)
                        for i in range(len(args)):
                            args[i], s = checker.check(
                                args[i], elem_ty.substitute(subst)
                            )
                            subst |= s
                        ls = unify(length, ConstValue(nat_type(), len(args)), {})
                        if ls is None:
                            raise GuppyTypeError(
                                TypeMismatchError(
                                    self.node, ty, array_type(elem_ty, len(args))
                                )
                            )
                        subst |= ls
                        type_args = [
                            TypeArg(elem_ty.substitute(subst)),
                            ConstValue(nat_type(), len(args)),
                        ]
                        call = GlobalCall(
                            def_id=self.func.id, args=args, type_args=type_args
                        )
                        return with_loc(self.node, call), subst
            case type_args:
                raise InternalGuppyError(f"Invalid array type args: {type_args}")

    def synthesize_array_comprehension(
        self, compr: DesugaredGeneratorExpr
    ) -> tuple[DesugaredArrayComp, Type]:
        # Array comprehensions require a static size. To keep things simple, we'll only
        # allow a single generator for now, so we don't have to reason about products
        # of iterator sizes.
        if len(compr.generators) > 1:
            # Individual generator objects unfortunately don't have a span in Python's
            # AST, so we have to use the whole expression span
            raise GuppyError(UnsupportedError(compr, "Nested array comprehensions"))
        [gen] = compr.generators
        # Similarly, dynamic if guards are not allowed
        if gen.ifs:
            err = ArrayComprUnknownSizeError(compr)
            err.add_sub_diagnostic(ArrayComprUnknownSizeError.IfGuard(gen.ifs[0]))
            raise GuppyError(err)
        # Extract the iterator size
        match gen.iter_assign:
            case ast.Assign(value=MakeIter() as make_iter):
                sized_make_iter = MakeIter(
                    make_iter.value, make_iter.origin_node, unwrap_size_hint=False
                )
                _, iter_ty = ExprSynthesizer(self.ctx).synthesize(sized_make_iter)
                # The iterator must have a static size hint
                if not is_sized_iter_type(iter_ty):
                    err = ArrayComprUnknownSizeError(compr)
                    err.add_sub_diagnostic(
                        ArrayComprUnknownSizeError.DynamicIterator(make_iter)
                    )
                    raise GuppyError(err)
                size = get_iter_size(iter_ty)
            case _:
                raise InternalGuppyError("Invalid iterator assign statement")
        # Finally, type check the comprehension
        [gen], elt, elt_ty = synthesize_comprehension(compr, [gen], compr.elt, self.ctx)
        array_compr = DesugaredArrayComp(
            elt=elt, generator=gen, length=size, elt_ty=elt_ty
        )
        return with_loc(compr, array_compr), array_type(elt_ty, size)


class PanicChecker(CustomCallChecker):
    """Call checker for the `panic`  function."""

    @dataclass(frozen=True)
    class NoMessageError(Error):
        title: ClassVar[str] = "No panic message"
        span_label: ClassVar[str] = "Missing message argument to panic call"

        @dataclass(frozen=True)
        class Suggestion(Note):
            message: ClassVar[str] = 'Add a message: `panic("message")`'

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        match args:
            case []:
                err = PanicChecker.NoMessageError(self.node)
                err.add_sub_diagnostic(PanicChecker.NoMessageError.Suggestion(None))
                raise GuppyTypeError(err)
            case [msg, *rest]:
                # Check type of message and synthesize types for additional values.
                msg, _ = ExprChecker(self.ctx).check(msg, string_type())
                vals = [ExprSynthesizer(self.ctx).synthesize(val)[0] for val in rest]
                # TODO variable signals once default arguments are available
                # TODO this will also allow us to remove this manual AST node hack
                signal_expr = with_type(
                    int_type(), with_loc(self.node, ast.Constant(value=1))
                )
                node = PanicExpr(
                    kind=ExitKind.Panic, msg=msg, values=vals, signal=signal_expr
                )
                return with_loc(self.node, node), NoneType()
            case args:
                return assert_never(args)  # type: ignore[arg-type]

    def check(self, args: list[ast.expr], ty: Type) -> tuple[ast.expr, Subst]:
        # Panic may return any type, so we don't have to check anything. Consequently
        # we also can't infer anything in the expected type, so we always return an
        # empty substitution
        expr, _ = self.synthesize(args)
        return expr, {}


class ExitChecker(CustomCallChecker):
    """Call checker for the ``exit` functions."""

    @dataclass(frozen=True)
    class NoMessageError(Error):
        title: ClassVar[str] = "No exit message"
        span_label: ClassVar[str] = "Missing message argument to exit call"

        @dataclass(frozen=True)
        class Suggestion(Note):
            message: ClassVar[str] = 'Add a message: `exit("message", 0)`'

    @dataclass(frozen=True)
    class NoSignalError(Error):
        title: ClassVar[str] = "No exit signal"
        span_label: ClassVar[str] = "Missing signal argument to exit call"

        @dataclass(frozen=True)
        class Suggestion(Note):
            message: ClassVar[str] = 'Add a signal: `exit("message", 0)`'

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        match args:
            case []:
                msg_err = ExitChecker.NoMessageError(self.node)
                msg_err.add_sub_diagnostic(ExitChecker.NoMessageError.Suggestion(None))
                raise GuppyTypeError(msg_err)
            case [_msg]:
                signal_err = ExitChecker.NoSignalError(self.node)
                signal_err.add_sub_diagnostic(
                    ExitChecker.NoSignalError.Suggestion(None)
                )
                raise GuppyTypeError(signal_err)
            case [msg, signal, *rest]:
                # Check types for message and signal and synthesize types for additional
                # values.
                msg, _ = ExprChecker(self.ctx).check(msg, string_type())
                signal, _ = ExprChecker(self.ctx).check(signal, int_type())
                vals = [ExprSynthesizer(self.ctx).synthesize(val)[0] for val in rest]
                node = PanicExpr(
                    kind=ExitKind.ExitShot,
                    msg=msg,
                    values=vals,
                    signal=signal,
                )
                return with_loc(self.node, node), NoneType()
            case args:
                return assert_never(args)  # type: ignore[arg-type]

    def check(self, args: list[ast.expr], ty: Type) -> tuple[ast.expr, Subst]:
        # Exit may return any type, so we don't have to check anything. Consequently
        # we also can't infer anything in the expected type, so we always return an
        # empty substitution
        expr, _ = self.synthesize(args)
        return expr, {}


def to_sized_iter(
    iterator: ast.expr, range_ty: Type, size: "int | Const", ctx: Context
) -> tuple[ast.expr, Type]:
    """Adds a static size annotation to an iterator."""
    sized_iter_ty = sized_iter_type(range_ty, size)
    make_sized_iter = ctx.globals.get_instance_func(sized_iter_ty, "__new__")
    assert make_sized_iter is not None
    sized_iter, _ = make_sized_iter.check_call([iterator], sized_iter_ty, iterator, ctx)
    return sized_iter, sized_iter_ty


class BarrierChecker(CustomCallChecker):
    """Call checker for the `barrier` function."""

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        tys = [ExprSynthesizer(self.ctx).synthesize(val)[1] for val in args]
        func_ty = FunctionType(
            [FuncInput(t, InputFlags.Inout) for t in tys],
            NoneType(),
        )
        args, ret_ty, inst = synthesize_call(func_ty, args, self.node, self.ctx)
        assert len(inst) == 0, "func_ty is not generic"
        node = BarrierExpr(args=args, func_ty=func_ty)
        return with_loc(self.node, node), ret_ty


class WasmCallChecker(CustomCallChecker):
    def check(self, args: list[ast.expr], ty: Type) -> tuple[ast.expr, Subst]:
        # Use default implementation from the expression checker
        args, subst, inst = check_call(self.func.ty, args, ty, self.node, self.ctx)

        return GlobalCall(def_id=self.func.id, args=args, type_args=inst), subst

    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        # Use default implementation from the expression checker
        args, ty, inst = synthesize_call(self.func.ty, args, self.node, self.ctx)
        return GlobalCall(def_id=self.func.id, args=args, type_args=inst), ty
