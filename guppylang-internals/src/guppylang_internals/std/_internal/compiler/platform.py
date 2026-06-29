import ast
from dataclasses import dataclass
from typing import ClassVar

import hugr
from hugr import Wire, ops, tys
from typing_extensions import override

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.errors.type_errors import TypeMismatchError
from guppylang_internals.checker.expr_checker import ExprSynthesizer
from guppylang_internals.compiler.core import CompilerContext
from guppylang_internals.definition.custom import (
    CustomCallChecker,
    CustomCallCompiler,
    CustomInoutCallCompiler,
)
from guppylang_internals.definition.value import CallReturnWires
from guppylang_internals.diagnostic import Error, Note
from guppylang_internals.error import (
    BypassOverloadError,
    GuppyError,
    GuppyTypeError,
    InternalGuppyError,
)
from guppylang_internals.std._internal.compiler.array import (
    array_clone,
    array_to_std_array,
)
from guppylang_internals.std._internal.compiler.tket_exts import RESULT_EXTENSION
from guppylang_internals.tys.arg import Argument, ConstArg
from guppylang_internals.tys.builtin import get_element_type, is_array_type
from guppylang_internals.tys.const import BoundConstVar, ConstValue
from guppylang_internals.tys.ty import NumericType, Type

#: Maximum length of a tag in the `output` function.
TAG_MAX_LEN = 200


@dataclass(frozen=True)
class OutputTagTooLongError(Error):
    title: ClassVar[str] = "Tag too long"
    span_label: ClassVar[str] = "Output tag is too long"

    @dataclass(frozen=True)
    class Hint(Note):
        message: ClassVar[str] = f"Output tags are limited to {TAG_MAX_LEN} bytes"


class OutputCompiler(CustomCallCompiler):
    """Custom compiler for overloads of the `output` function.

    See `ArrayOutputCompiler` for the compiler that handles outputs involving arrays.
    """

    def __init__(self, op_name: str, with_int_width: bool = False):
        self.op_name = op_name
        self.with_int_width = with_int_width

    def compile(self, args: list[Wire]) -> list[Wire]:
        assert self.func is not None
        [value] = args
        ty = self.func.ty.inputs[1].ty
        hugr_ty = ty.to_hugr(self.ctx)
        args = [tag_to_hugr(self.type_args[0], self.ctx, self.node)]
        if self.with_int_width:
            args.append(tys.BoundedNatArg(NumericType.INT_WIDTH))
        op = RESULT_EXTENSION.get_op(self.op_name)
        sig = tys.FunctionType(input=[hugr_ty], output=[])
        self.builder.add_op(op.instantiate(args, sig), value)
        return []


class ArrayOutputCompiler(CustomInoutCallCompiler):
    """Custom compiler for overloads of the `output` function accepting arrays.

    See `OutputCompiler` for the compiler that handles basic outputs.
    """

    def __init__(self, op_name: str, with_int_width: bool = False):
        self.op_name = op_name
        self.with_int_width = with_int_width

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        assert self.func is not None
        array_ty = self.func.ty.inputs[1].ty
        elem_ty = get_element_type(array_ty)
        [tag_arg, size_arg] = self.type_args
        [arr] = args

        # As `borrow_array`s used by Guppy are linear, we need to clone it (knowing
        # that all elements in it are copyable) to avoid linearity violations when
        # both passing it to the output operation and returning it (as an inout
        # argument).
        hugr_elem_ty = elem_ty.to_hugr(self.ctx)
        hugr_size = size_arg.to_hugr(self.ctx)
        arr, out_arr = self.builder.add_op(array_clone(hugr_elem_ty, hugr_size), arr)
        # Turn `borrow_array` into regular `array`
        arr = self.builder.add_op(array_to_std_array(hugr_elem_ty, hugr_size), arr).out(
            0
        )

        hugr_ty = hugr.std.collections.array.Array(hugr_elem_ty, hugr_size)
        sig = tys.FunctionType(input=[hugr_ty], output=[])
        args = [tag_to_hugr(tag_arg, self.ctx, self.node), hugr_size]
        if self.with_int_width:
            args.append(tys.BoundedNatArg(NumericType.INT_WIDTH))
        op = ops.ExtOp(RESULT_EXTENSION.get_op(self.op_name), signature=sig, args=args)
        self.builder.add_op(op, arr)
        return CallReturnWires([], [out_arr])


def tag_to_hugr(tag_arg: Argument, ctx: CompilerContext, loc: AstNode) -> tys.TypeArg:
    """Helper function to convert the Guppy tag comptime argument into a Hugr type arg.

    Takes care of reading the tag value from the current monomorphization and checks
    that the tag fits into `TAG_MAX_LEN`.
    """
    match tag_arg:
        case ConstArg(const=ConstValue(value=str(value))):
            tag = value
        case ConstArg(const=BoundConstVar()):
            raise InternalGuppyError("Tag should be monomorphized at this point")
        case _:
            raise InternalGuppyError("Invalid tag argument")

    if len(tag.encode("utf-8")) > TAG_MAX_LEN:
        err = OutputTagTooLongError(loc)
        err.add_sub_diagnostic(OutputTagTooLongError.Hint(None))
        raise GuppyError(err)
    return tys.StringArg(tag)


class MeasurementOutputChecker(CustomCallChecker):
    """Call checker enabling an additional hint when rejecting `Measurement` values
    from the overloaded `output` function.
    """

    exclude_from_overload_hints = True

    @dataclass(frozen=True)
    class MeasurementOutputError(Error):
        title: ClassVar[str] = "Unsupported output value type"
        span_label: ClassVar[str] = (
            "Values of type `Measurement` cannot be passed to `output` directly"
        )

        @dataclass(frozen=True)
        class ReadHint(Note):
            message: ClassVar[str] = (
                "Use `.read()` on the value to get a bool (this will block execution "
                "until the measurement result is available)"
            )

        @dataclass(frozen=True)
        class ReadArrayHint(Note):
            message: ClassVar[str] = (
                "Use `collect_measurements()` on the array to get an array of bools "
                "(this will block execution until all the measurement results are "
                "available)"
            )

    @override
    def synthesize(self, args: list[ast.expr]) -> tuple[ast.expr, Type]:
        # Type-check the given value against the expected type (either `Measurement` or
        # `array[Measurement, n]`).
        _, arg_ty = ExprSynthesizer(self.ctx).synthesize(args[1])
        expected_ty = self.func.ty.inputs[1].ty
        is_array = is_array_type(arg_ty)

        if is_array:
            if (not is_array_type(expected_ty)) or (
                get_element_type(arg_ty) != get_element_type(expected_ty)
            ):
                raise GuppyTypeError(TypeMismatchError(self.node, expected_ty, arg_ty))
        elif arg_ty != expected_ty:
            raise GuppyTypeError(TypeMismatchError(self.node, expected_ty, arg_ty))

        # Raise an error that can bypass the default overload error suppression so we
        # can provide a more specific hint to the user.
        err = MeasurementOutputChecker.MeasurementOutputError(self.node)
        if is_array:
            err.add_sub_diagnostic(
                MeasurementOutputChecker.MeasurementOutputError.ReadArrayHint(None)
            )
        else:
            err.add_sub_diagnostic(
                MeasurementOutputChecker.MeasurementOutputError.ReadHint(None)
            )
        raise BypassOverloadError(err)
