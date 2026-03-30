"""Compilers building array functions on top of hugr standard operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, TypeVar

import hugr.std.collections
import hugr.std.int
import hugr.std.prelude
from hugr import Node, Wire, ops
from hugr import tys as ht
from hugr import val as hv

from guppylang_internals.compiler.core import (
    CompilerContext,
    DFBuilder,
    GlobalConstId,
)
from guppylang_internals.definition.custom import (
    CustomCallCompiler,
    CustomInoutCallCompiler,
)
from guppylang_internals.definition.value import CallReturnWires
from guppylang_internals.error import InternalGuppyError
from guppylang_internals.nodes import AbortKind

if TYPE_CHECKING:
    from collections.abc import Callable

    from hugr.build import function as hf
    from hugr.build.dfg import DfBase

    from guppylang_internals.tys.common import ToHugrContext
    from guppylang_internals.tys.subst import Inst


# --------------------------------------------
# --------------- prelude --------------------
# --------------------------------------------


def error_type() -> ht.ExtType:
    """Returns the hugr type of an error value."""
    return hugr.std.PRELUDE.types["error"].instantiate([])


@dataclass
class ErrorVal(hv.ExtensionValue):
    """Custom value for a floating point number."""

    signal: int
    message: str

    def to_value(self) -> hv.Extension:
        name = "ConstError"
        payload = {"signal": self.signal, "message": self.message}
        return hv.Extension(name, typ=error_type(), val=payload)

    def __str__(self) -> str:
        return f"Error({self.signal}): {self.message}"


def panic(
    inputs: list[ht.Type], outputs: list[ht.Type], kind: AbortKind = AbortKind.Panic
) -> ops.ExtOp:
    """Returns an operation that panics."""
    name = "panic" if kind == AbortKind.Panic else "exit"
    op_def = hugr.std.PRELUDE.get_op(name)
    args: list[ht.TypeArg] = [
        ht.ListArg([ht.TypeTypeArg(ty) for ty in inputs]),
        ht.ListArg([ht.TypeTypeArg(ty) for ty in outputs]),
    ]
    sig = ht.FunctionType([error_type(), *inputs], outputs)
    return ops.ExtOp(op_def, sig, args)


def make_error() -> ops.ExtOp:
    """Returns an operation that makes an error."""
    op_def = hugr.std.PRELUDE.get_op("MakeError")
    args: list[ht.TypeArg] = []
    sig = ht.FunctionType([ht.USize(), hugr.std.prelude.STRING_T], [error_type()])
    return ops.ExtOp(op_def, sig, args)


# ------------------------------------------------------
# --------- Custom compilers for non-native ops --------
# ------------------------------------------------------

P = TypeVar("P", bound=ops.DfParentOp)


def build_panic(
    builder: DFBuilder[P],
    in_tys: ht.TypeRow,
    out_tys: ht.TypeRow,
    err: Wire,
    *args: Wire,
) -> Node:
    """Builds a panic operation."""
    op = panic(in_tys, out_tys, AbortKind.Panic)
    return builder.add_op(op, err, *args)


def build_static_error(builder: DfBase[P], signal: int, msg: str) -> Wire:
    """Constructs and loads a static error value."""
    val = ErrorVal(signal, msg)
    return builder.load(builder.add_const(val))


def build_unwrap_either(
    builder: DFBuilder[P],
    either: Wire,
    left: bool,
    error_msg: str,
    error_signal: int = 1,
) -> Node:
    """Unwraps the left or right value from a `hugr.tys.Either` value according to the
    `left` flag, panicking with the given message if the result is on the other side.
    """
    conditional = builder.add_conditional(either)
    result_ty = builder.get_wire_type(either)
    assert isinstance(result_ty, ht.Sum)
    [left_tys, right_tys] = result_ty.variant_rows
    [in_tys, out_tys] = [right_tys, left_tys] if left else [left_tys, right_tys]
    ok_case_num = 0 if left else 1
    panic_case_num = 1 - ok_case_num
    with conditional.add_case(ok_case_num) as case:
        case.set_outputs(*case.inputs())
    with conditional.add_case(panic_case_num) as case:
        error = build_static_error(case, error_signal, error_msg)
        case.set_outputs(
            *build_panic(
                DFBuilder(case, builder.current_ast_node),
                in_tys,
                out_tys,
                error,
                *case.inputs(),
            )
        )
    return conditional.to_node()


def build_unwrap_left(
    builder: DFBuilder[P], either: Wire, error_msg: str, error_signal: int = 1
) -> Node:
    """Unwraps the left value from a `hugr.tys.Either` value, panicking with the given
    message if the result is right.
    """
    return build_unwrap_either(
        builder,
        either,
        left=True,
        error_msg=error_msg,
        error_signal=error_signal,
    )


def build_unwrap_right(
    builder: DFBuilder[P],
    either: Wire,
    error_msg: str,
    error_signal: int = 1,
) -> Node:
    """Unwraps the right value from a `hugr.tys.Either` value, panicking with the given
    message if the result is left.
    """
    return build_unwrap_either(
        builder,
        either,
        left=False,
        error_msg=error_msg,
        error_signal=error_signal,
    )


def build_unwrap(
    builder: DFBuilder[P],
    option: Wire,
    error_msg: str,
    error_signal: int = 1,
) -> Node:
    """Unwraps an `hugr.tys.Option` value, panicking with the given message if the
    result is an error.
    """
    return build_unwrap_right(
        builder,
        option,
        error_msg=error_msg,
        error_signal=error_signal,
    )


def build_expect_none(
    builder: DFBuilder[P],
    option: Wire,
    error_msg: str,
    error_signal: int = 1,
) -> Node:
    """Checks that `hugr.tys.Option` value is `None`, otherwise panics with the given
    message.
    """
    return build_unwrap_left(
        builder,
        option,
        error_msg=error_msg,
        error_signal=error_signal,
    )


class MemSwapCompiler(CustomCallCompiler):
    """Compiler for the `mem_swap` function."""

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [x, y] = args
        return CallReturnWires(regular_returns=[], inout_returns=[y, x])

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


UNWRAP_RESULT: Final[GlobalConstId] = GlobalConstId.fresh("unwrap_result")


def _build_unwrap_result(func: hf.Function, result_type_var: ht.Variable) -> None:
    either = func.inputs()[0]
    conditional = func.add_conditional(either)
    with conditional.add_case(0) as case:
        [error] = list(case.inputs())
        case.set_outputs(
            *build_panic(
                # We don't want misleading debug info in global functions until
                # https://github.com/Quantinuum/guppylang/issues/1609 is implemented,
                # so `current_ast_node`is None here by default
                DFBuilder(case),
                [error_type()],
                [result_type_var],
                error,
                *case.inputs(),
            )
        )
    with conditional.add_case(1) as case:
        case.set_outputs(*case.inputs())
    func.set_outputs(*conditional.outputs())


def unwrap_result(
    builder: DFBuilder[P],
    ctx: CompilerContext,
    either: Wire,
) -> Wire:
    """Builds or retrieves and then calls a function that unwraps an `hugr.tys.Either`
    value, panicking if the result is an error.
    """
    either_ty = builder.get_wire_type(either)
    assert isinstance(either_ty, ht.Either)
    [error_tys, result_tys] = either_ty.variant_rows
    # Construct the function signature for unwrapping a result of type T.
    func_ty = ht.PolyFuncType(
        params=[ht.TypeTypeParam(ht.TypeBound.Linear)],
        body=ht.FunctionType(
            input=[ht.Either(error_tys, [ht.Variable(0, ht.TypeBound.Linear)])],
            output=[ht.Variable(0, ht.TypeBound.Linear)],
        ),
    )
    # Build global unwrap result function if it doesn't already exist.
    func, already_exists = ctx.declare_global_func(UNWRAP_RESULT, func_ty)
    if not already_exists:
        _build_unwrap_result(func, ht.Variable(0, ht.TypeBound.Linear))
    # Call the global function.
    concrete_ty = ht.FunctionType(
        input=[ht.Either(error_tys, result_tys)], output=result_tys
    )
    type_args = [ht.TypeTypeArg(*result_tys)]
    func_call = builder.call(
        func.parent_node,
        either,
        instantiation=concrete_ty,
        type_args=type_args,
    )
    [result] = list(func_call.outputs())
    return result


class UnwrapOpCompiler(CustomInoutCallCompiler):
    """Compiler for operations that require unwrapping a result which could potentially
    cause a panic.

    Args:
        op: A HUGR operation that outputs an Either<error, result> value.
    """

    op: Callable[[ht.FunctionType, Inst, ToHugrContext], ops.DataflowOp]

    def __init__(
        self, op: Callable[[ht.FunctionType, Inst, ToHugrContext], ops.DataflowOp]
    ):
        self.op = op

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        assert len(self.ty.output) == 1
        # To instantiate the op we need a function signature that wraps the output of
        # the function that is being compiled into an either type.
        opt_func_type = ht.FunctionType(
            input=self.ty.input,
            output=[ht.Either([error_type()], self.ty.output)],
        )
        op = self.op(opt_func_type, self.type_args, self.ctx)
        either = self.builder.add_op(op, *args)
        result = unwrap_result(self.builder, self.ctx, either)
        return CallReturnWires(regular_returns=[result], inout_returns=[])


class BarrierCompiler(CustomCallCompiler):
    """Compiler for the `barrier` function."""

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        tys = [t for arg in args if (t := self.builder.get_wire_type(arg))]

        op = hugr.std.prelude.PRELUDE_EXTENSION.get_op("Barrier").instantiate(
            [ht.ListArg([ht.TypeTypeArg(ty) for ty in tys])]
        )

        barrier_n = self.builder.add_op(op, *args)

        return CallReturnWires(
            regular_returns=[], inout_returns=[barrier_n[i] for i in range(len(tys))]
        )

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")
