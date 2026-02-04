"""Native arithmetic operations from the HUGR std, and compilers for non native ones."""

from collections.abc import Sequence
from dataclasses import dataclass

import hugr.std.int
from hugr import model, ops, val
from hugr import tys as ht
from hugr.std.int import int_t

from guppylang_internals.std._internal.compiler.prelude import error_type
from guppylang_internals.tys.ty import NumericType

INT_T = int_t(NumericType.INT_WIDTH)


@dataclass
class UnsignedIntVal(val.ExtensionValue):  # TODO: Upstream this to hugr-py?
    """Custom value for an unsigned integer."""

    v: int
    width: int

    def __post_init__(self) -> None:
        assert self.v >= 0

    def to_value(self) -> val.Extension:
        payload = {"log_width": self.width, "value": self.v}
        return val.Extension("ConstInt", typ=int_t(self.width), val=payload)

    def __str__(self) -> str:
        return f"{self.v}"

    def to_model(self) -> model.Term:
        return model.Apply(
            "arithmetic.int.const", [model.Literal(self.width), model.Literal(self.v)]
        )


# ------------------------------------------------------
# --------- std.arithmetic.int operations --------------
# ------------------------------------------------------


def _instantiate_int_op(
    name: str,
    int_width: int | Sequence[int],
    inp: list[ht.Type],
    out: list[ht.Type],
) -> ops.ExtOp:
    op_def = hugr.std.int.INT_OPS_EXTENSION.get_op(name)
    int_width = [int_width] if isinstance(int_width, int) else int_width
    return ops.ExtOp(
        op_def,
        ht.FunctionType(inp, out),
        [ht.BoundedNatArg(w) for w in int_width],
    )


def ieq(width: int) -> ops.ExtOp:
    """Returns a `std.arithmetic.int.ieq` operation."""
    return _instantiate_int_op("ieq", width, [int_t(width), int_t(width)], [ht.Bool])


def ine(width: int) -> ops.ExtOp:
    """Returns a `std.arithmetic.int.ine` operation."""
    return _instantiate_int_op("ine", width, [int_t(width), int_t(width)], [ht.Bool])


def iwiden_u(from_width: int, to_width: int) -> ops.ExtOp:
    """Returns an unsigned `std.arithmetic.int.widen_u` operation."""
    return _instantiate_int_op(
        "iwiden_u", [from_width, to_width], [int_t(from_width)], [int_t(to_width)]
    )


def iwiden_s(from_width: int, to_width: int) -> ops.ExtOp:
    """Returns a signed `std.arithmetic.int.widen_s` operation."""
    return _instantiate_int_op(
        "iwiden_s", [from_width, to_width], [int_t(from_width)], [int_t(to_width)]
    )


def inarrow_u(from_width: int, to_width: int) -> ops.ExtOp:
    """Returns an unsigned `std.arithmetic.int.narrow_u` operation."""
    return _instantiate_int_op(
        "inarrow_u",
        [from_width, to_width],
        [int_t(from_width)],
        [ht.Either([error_type()], [int_t(to_width)])],
    )


def inarrow_s(from_width: int, to_width: int) -> ops.ExtOp:
    """Returns a signed `std.arithmetic.int.narrow_s` operation."""
    return _instantiate_int_op(
        "inarrow_s",
        [from_width, to_width],
        [int_t(from_width)],
        [ht.Either([error_type()], [int_t(to_width)])],
    )


# ------------------------------------------------------
# --------- std.arithmetic.conversions ops -------------
# ------------------------------------------------------


def _instantiate_convert_op(
    name: str,
    inp: list[ht.Type],
    out: list[ht.Type],
    args: list[ht.TypeArg] | None = None,
) -> ops.ExtOp:
    op_def = hugr.std.int.CONVERSIONS_EXTENSION.get_op(name)
    return ops.ExtOp(op_def, ht.FunctionType(inp, out), args or [])


def convert_ifromusize() -> ops.ExtOp:
    """Returns a `std.arithmetic.conversions.ifromusize` operation."""
    return _instantiate_convert_op("ifromusize", [ht.USize()], [INT_T])


def convert_itousize() -> ops.ExtOp:
    """Returns a `std.arithmetic.conversions.itousize` operation."""
    return _instantiate_convert_op("itousize", [INT_T], [ht.USize()])


def convert_ifrombool() -> ops.ExtOp:
    """Returns a `std.arithmetic.conversions.ifrombool` operation."""
    return _instantiate_convert_op("ifrombool", [ht.Bool], [int_t(0)])


def convert_itobool() -> ops.ExtOp:
    """Returns a `std.arithmetic.conversions.itobool` operation."""
    return _instantiate_convert_op("itobool", [int_t(0)], [ht.Bool])
