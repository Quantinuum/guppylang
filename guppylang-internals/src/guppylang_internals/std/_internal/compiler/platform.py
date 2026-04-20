from dataclasses import dataclass
from typing import ClassVar

import hugr
from hugr import Wire, ops, tys

from guppylang_internals.ast_util import AstNode
from guppylang_internals.compiler.core import CompilerContext
from guppylang_internals.compiler.expr_compiler import array_read_bool
from guppylang_internals.definition.custom import (
    CustomCallCompiler,
    CustomInoutCallCompiler,
)
from guppylang_internals.definition.value import CallReturnWires
from guppylang_internals.diagnostic import Error, Note
from guppylang_internals.error import GuppyError, InternalGuppyError
from guppylang_internals.std._internal.compiler.array import (
    array_clone,
    array_map,
    array_to_std_array,
)
from guppylang_internals.std._internal.compiler.tket_bool import OpaqueBool, read_bool
from guppylang_internals.std._internal.compiler.tket_exts import RESULT_EXTENSION
from guppylang_internals.tys.arg import Argument, ConstArg
from guppylang_internals.tys.builtin import get_element_type, is_bool_type
from guppylang_internals.tys.const import BoundConstVar, ConstValue
from guppylang_internals.tys.ty import NumericType

#: Maximum length of a tag in the `result` function.
TAG_MAX_LEN = 200


@dataclass(frozen=True)
class TooLongError(Error):
    title: ClassVar[str] = "Tag too long"
    span_label: ClassVar[str] = "Result tag is too long"

    @dataclass(frozen=True)
    class Hint(Note):
        message: ClassVar[str] = f"Result tags are limited to {TAG_MAX_LEN} bytes"

    @dataclass(frozen=True)
    class GenericHint(Note):
        message: ClassVar[str] = "Parameter `{param}` was instantiated to `{value}`"
        param: str
        value: str


class ResultCompiler(CustomCallCompiler):
    """Custom compiler for overloads of the `result` function.

    See `ArrayResultCompiler` for the compiler that handles results involving arrays.
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
        # Bool results need an extra conversion into regular hugr bools
        if is_bool_type(ty):
            value = self.builder.add_op(read_bool(), value)
            hugr_ty = tys.Bool
        op = RESULT_EXTENSION.get_op(self.op_name)
        sig = tys.FunctionType(input=[hugr_ty], output=[])
        self.builder.add_op(op.instantiate(args, sig), value)
        return []


class ArrayResultCompiler(CustomInoutCallCompiler):
    """Custom compiler for overloads of the `result` function accepting arrays.

    See `ResultCompiler` for the compiler that handles basic results.
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
        # both passing it to the result operation and returning it (as an inout
        # argument).
        hugr_elem_ty = elem_ty.to_hugr(self.ctx)
        hugr_size = size_arg.to_hugr(self.ctx)
        arr, out_arr = self.builder.add_op(array_clone(hugr_elem_ty, hugr_size), arr)
        # For bool arrays, we furthermore need to coerce a read on all the array
        # elements
        if is_bool_type(elem_ty):
            array_read = array_read_bool(self.ctx)
            array_read = self.builder.load_function(array_read)
            map_op = array_map(OpaqueBool, hugr_size, tys.Bool)
            arr = self.builder.add_op(map_op, arr, array_read).out(0)
            hugr_elem_ty = tys.Bool
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
    is_generic: BoundConstVar | None = None
    match tag_arg:
        case ConstArg(const=ConstValue(value=str(value))):
            tag = value
        case ConstArg(const=BoundConstVar(idx=idx) as var):
            is_generic = var
            assert ctx.current_mono_args is not None
            match ctx.current_mono_args[idx]:
                case ConstArg(const=ConstValue(value=str(value))):
                    tag = value
                case _:
                    raise InternalGuppyError("Invalid tag monomorphization")
        case _:
            raise InternalGuppyError("Invalid tag argument")

    if len(tag.encode("utf-8")) > TAG_MAX_LEN:
        err = TooLongError(loc)
        err.add_sub_diagnostic(TooLongError.Hint(None))
        if is_generic:
            err.add_sub_diagnostic(
                TooLongError.GenericHint(None, is_generic.display_name, tag)
            )
        raise GuppyError(err)
    return tys.StringArg(tag)
