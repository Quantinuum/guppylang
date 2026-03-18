"""Numeric types and methods."""

# ruff: noqa: E501
# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def, has-type"

from __future__ import annotations

from typing import no_type_check

import hugr.std.int
from guppylang_internals.decorator import custom_function, extend_type, hugr_op
from guppylang_internals.definition.custom import BoolOpCompiler, NoopCompiler
from guppylang_internals.std._internal.checker import DunderChecker, ReversingChecker
from guppylang_internals.std._internal.compiler.prelude import UnwrapOpCompiler
from guppylang_internals.std._internal.util import (
    external_op,
    float_op,
    int_op,
    unsupported_op,
)
from guppylang_internals.tys.builtin import float_type_def, int_type_def, nat_type_def

from guppylang import guppy


@extend_type(nat_type_def)
class nat:
    """A 64-bit unsigned integer."""

    @custom_function(NoopCompiler())
    def __abs__(self: nat) -> nat: ...

    @hugr_op(int_op("iadd"))
    def __add__(self: nat, other: nat) -> nat: ...

    @hugr_op(int_op("iand"))
    def __and__(self: nat, other: nat) -> nat: ...

    @guppy
    @no_type_check
    def __bool__(self: nat) -> bool:
        return self != 0

    @custom_function(NoopCompiler())
    def __ceil__(self: nat) -> nat: ...

    @hugr_op(int_op("idivmod_u", n_vars=2))
    def __divmod__(self: nat, other: nat) -> tuple[nat, nat]: ...

    @custom_function(BoolOpCompiler(int_op("ieq")))
    def __eq__(self: nat, other: nat) -> bool: ...

    @hugr_op(int_op("convert_u", hugr.std.int.CONVERSIONS_EXTENSION))
    def __float__(self: nat) -> float: ...

    @custom_function(NoopCompiler())
    def __floor__(self: nat) -> nat: ...

    @hugr_op(int_op("idiv_u"))
    def __floordiv__(self: nat, other: nat) -> nat: ...

    @custom_function(BoolOpCompiler(int_op("ige_u")))
    def __ge__(self: nat, other: nat) -> bool: ...

    @custom_function(BoolOpCompiler(int_op("igt_u")))
    def __gt__(self: nat, other: nat) -> bool: ...

    @hugr_op(int_op("iu_to_s"))
    def __int__(self: nat) -> int: ...

    @hugr_op(int_op("inot"))
    def __invert__(self: nat) -> nat: ...

    @custom_function(BoolOpCompiler(int_op("ile_u")))
    def __le__(self: nat, other: nat) -> bool: ...

    @hugr_op(int_op("ishl"))
    def __lshift__(self: nat, other: nat) -> nat: ...

    @custom_function(BoolOpCompiler(int_op("ilt_u")))
    def __lt__(self: nat, other: nat) -> bool: ...

    @hugr_op(int_op("imod_u"))
    def __mod__(self: nat, other: nat) -> nat: ...

    @hugr_op(int_op("imul"))
    def __mul__(self: nat, other: nat) -> nat: ...

    @custom_function(NoopCompiler())
    def __nat__(self: nat) -> nat: ...

    @custom_function(BoolOpCompiler(int_op("ine")))
    def __ne__(self: nat, other: nat) -> bool: ...

    @custom_function(checker=DunderChecker("__nat__"), higher_order_value=False)
    def __new__(x): ...

    @hugr_op(int_op("ior"))
    def __or__(self: nat, other: nat) -> nat: ...

    @custom_function(NoopCompiler())
    def __pos__(self: nat) -> nat: ...

    @hugr_op(int_op("ipow"))
    def __pow__(self: nat, other: nat) -> nat: ...

    @custom_function(checker=ReversingChecker())
    def __radd__(self: nat, other: nat) -> nat: ...

    @custom_function(checker=ReversingChecker())
    def __rand__(self: nat, other: nat) -> nat: ...

    @custom_function(checker=ReversingChecker())
    def __rdivmod__(self: nat, other: nat) -> tuple[nat, nat]: ...

    @custom_function(checker=ReversingChecker())
    def __rfloordiv__(self: nat, other: nat) -> nat: ...

    @custom_function(checker=ReversingChecker())
    def __rlshift__(self: nat, other: nat) -> nat: ...

    @custom_function(checker=ReversingChecker())
    def __rmod__(self: nat, other: nat) -> nat: ...

    @custom_function(checker=ReversingChecker())
    def __rmul__(self: nat, other: nat) -> nat: ...

    @custom_function(checker=ReversingChecker())
    def __ror__(self: nat, other: nat) -> nat: ...

    @custom_function(NoopCompiler())
    def __round__(self: nat) -> nat: ...

    @custom_function(checker=ReversingChecker())
    def __rpow__(self: nat, other: nat) -> nat: ...

    @custom_function(checker=ReversingChecker())
    def __rrshift__(self: nat, other: nat) -> nat: ...

    @hugr_op(int_op("ishr"))
    def __rshift__(self: nat, other: nat) -> nat: ...

    @custom_function(checker=ReversingChecker())
    def __rsub__(self: nat, other: nat) -> nat: ...

    @custom_function(checker=ReversingChecker())
    def __rtruediv__(self: nat, other: nat) -> float: ...

    @custom_function(checker=ReversingChecker())
    def __rxor__(self: nat, other: nat) -> nat: ...

    @hugr_op(int_op("isub"))
    def __sub__(self: nat, other: nat) -> nat: ...

    @guppy
    @no_type_check
    def __truediv__(self: nat, other: nat) -> float:
        return float(self) / float(other)

    @custom_function(NoopCompiler())
    def __trunc__(self: nat) -> nat: ...

    @hugr_op(int_op("ixor"))
    def __xor__(self: nat, other: nat) -> nat: ...


@extend_type(int_type_def)
class int:
    """A 64-bit signed integer."""

    @hugr_op(int_op("iabs"))  # TODO: Maybe wrong? (signed vs unsigned!)
    def __abs__(self: int) -> int: ...

    @hugr_op(int_op("iadd"))
    def __add__(self: int, other: int) -> int: ...

    @hugr_op(int_op("iand"))
    def __and__(self: int, other: int) -> int: ...

    @guppy
    @no_type_check
    def __bool__(self: int) -> bool:
        return self != 0

    @custom_function(NoopCompiler())
    def __ceil__(self: int) -> int: ...

    @hugr_op(int_op("idivmod_s"))
    def __divmod__(self: int, other: int) -> tuple[int, int]: ...

    @custom_function(BoolOpCompiler(int_op("ieq")))
    def __eq__(self: int, other: int) -> bool: ...

    @hugr_op(int_op("convert_s", hugr.std.int.CONVERSIONS_EXTENSION))
    def __float__(self: int) -> float: ...

    @custom_function(NoopCompiler())
    def __floor__(self: int) -> int: ...

    @hugr_op(int_op("idiv_s"))
    def __floordiv__(self: int, other: int) -> int: ...

    @custom_function(BoolOpCompiler(int_op("ige_s")))
    def __ge__(self: int, other: int) -> bool: ...

    @custom_function(BoolOpCompiler(int_op("igt_s")))
    def __gt__(self: int, other: int) -> bool: ...

    @custom_function(NoopCompiler())
    def __int__(self: int) -> int: ...

    @hugr_op(int_op("inot"))
    def __invert__(self: int) -> int: ...

    @custom_function(BoolOpCompiler(int_op("ile_s")))
    def __le__(self: int, other: int) -> bool: ...

    @hugr_op(int_op("ishl"))  # TODO: RHS is unsigned
    def __lshift__(self: int, other: int) -> int: ...

    @custom_function(BoolOpCompiler(int_op("ilt_s")))
    def __lt__(self: int, other: int) -> bool: ...

    @hugr_op(int_op("imod_s"))
    def __mod__(self: int, other: int) -> int: ...

    @hugr_op(int_op("imul"))
    def __mul__(self: int, other: int) -> int: ...

    @hugr_op(int_op("is_to_u"))
    def __nat__(self: int) -> nat: ...

    @custom_function(BoolOpCompiler(int_op("ine")))
    def __ne__(self: int, other: int) -> bool: ...

    @hugr_op(int_op("ineg"))
    def __neg__(self: int) -> int: ...

    @custom_function(checker=DunderChecker("__int__"), higher_order_value=False)
    def __new__(x): ...

    @hugr_op(int_op("ior"))
    def __or__(self: int, other: int) -> int: ...

    @custom_function(NoopCompiler())
    def __pos__(self: int) -> int: ...

    @guppy
    @no_type_check
    def __pow__(self: int, exponent: int) -> int:
        if exponent < 0:
            panic(
                "Negative exponent not supported in"
                "__pow__ with int type base. Try casting the base to float."
            )
        return self.__pow_impl(exponent)

    @hugr_op(int_op("ipow"))
    def __pow_impl(self: int, exponent: int) -> int: ...

    @custom_function(checker=ReversingChecker())
    def __radd__(self: int, other: int) -> int: ...

    @custom_function(checker=ReversingChecker())
    def __rand__(self: int, other: int) -> int: ...

    @custom_function(checker=ReversingChecker())
    def __rdivmod__(self: int, other: int) -> tuple[int, int]: ...

    @custom_function(checker=ReversingChecker())
    def __rfloordiv__(self: int, other: int) -> int: ...

    @custom_function(checker=ReversingChecker())  # TODO: RHS is unsigned
    def __rlshift__(self: int, other: int) -> int: ...

    @custom_function(checker=ReversingChecker())
    def __rmod__(self: int, other: int) -> int: ...

    @custom_function(checker=ReversingChecker())
    def __rmul__(self: int, other: int) -> int: ...

    @custom_function(checker=ReversingChecker())
    def __ror__(self: int, other: int) -> int: ...

    @custom_function(NoopCompiler())
    def __round__(self: int) -> int: ...

    @custom_function(checker=ReversingChecker())
    def __rpow__(self: int, other: int) -> int: ...

    @custom_function(checker=ReversingChecker())  # TODO: RHS is unsigned
    def __rrshift__(self: int, other: int) -> int: ...

    @hugr_op(int_op("ishr"))  # TODO: RHS is unsigned
    def __rshift__(self: int, other: int) -> int: ...

    @custom_function(checker=ReversingChecker())
    def __rsub__(self: int, other: int) -> int: ...

    @custom_function(checker=ReversingChecker())
    def __rtruediv__(self: int, other: int) -> float: ...

    @custom_function(checker=ReversingChecker())
    def __rxor__(self: int, other: int) -> int: ...

    @hugr_op(int_op("isub"))
    def __sub__(self: int, other: int) -> int: ...

    @guppy
    @no_type_check
    def __truediv__(self: int, other: int) -> float:
        return float(self) / float(other)

    @custom_function(NoopCompiler())
    def __trunc__(self: int) -> int: ...

    @hugr_op(int_op("ixor"))
    def __xor__(self: int, other: int) -> int: ...


@extend_type(float_type_def)
class float:
    """An IEEE754 double-precision floating point value."""

    @hugr_op(float_op("fabs"))
    def __abs__(self: float) -> float: ...

    @hugr_op(float_op("fadd"))
    def __add__(self: float, other: float) -> float: ...

    @guppy
    @no_type_check
    def __bool__(self: float) -> bool:
        return self != 0.0

    @hugr_op(float_op("fceil"))
    def __ceil__(self: float) -> float: ...

    @guppy
    @no_type_check
    def __divmod__(self: float, other: float) -> tuple[float, float]:
        return self // other, self.__mod__(other)

    @custom_function(BoolOpCompiler(float_op("feq")))
    def __eq__(self: float, other: float) -> bool: ...

    @custom_function(NoopCompiler())
    def __float__(self: float) -> float: ...

    @hugr_op(float_op("ffloor"))
    def __floor__(self: float) -> float: ...

    @guppy
    @no_type_check
    def __floordiv__(self: float, other: float) -> float:
        return (self / other).__floor__()

    @custom_function(BoolOpCompiler(float_op("fge")))
    def __ge__(self: float, other: float) -> bool: ...

    @custom_function(BoolOpCompiler(float_op("fgt")))
    def __gt__(self: float, other: float) -> bool: ...

    @custom_function(
        UnwrapOpCompiler(
            # Use `int_op` to instantiate type arg with 64-bit integer.
            int_op("trunc_s", hugr.std.int.CONVERSIONS_EXTENSION),
        )
    )
    def __int__(self: float) -> int: ...

    @custom_function(BoolOpCompiler(float_op("fle")))
    def __le__(self: float, other: float) -> bool: ...

    @custom_function(BoolOpCompiler(float_op("flt")))
    def __lt__(self: float, other: float) -> bool: ...

    @guppy
    @no_type_check
    def __mod__(self: float, other: float) -> float:
        return self - (self // other) * other

    @hugr_op(float_op("fmul"))
    def __mul__(self: float, other: float) -> float: ...

    @custom_function(
        UnwrapOpCompiler(
            # Use `int_op` to instantiate type arg with 64-bit integer.
            int_op("trunc_u", hugr.std.int.CONVERSIONS_EXTENSION),
        )
    )
    def __nat__(self: float) -> nat: ...

    @custom_function(BoolOpCompiler(float_op("fne")))
    def __ne__(self: float, other: float) -> bool: ...

    @hugr_op(float_op("fneg"))
    def __neg__(self: float) -> float: ...

    @custom_function(checker=DunderChecker("__float__"), higher_order_value=False)
    def __new__(x): ...

    @custom_function(NoopCompiler())
    def __pos__(self: float) -> float: ...

    @hugr_op(float_op("fpow"))  # TODO
    def __pow__(self: float, other: float) -> float: ...

    @custom_function(checker=ReversingChecker())
    def __radd__(self: float, other: float) -> float: ...

    @custom_function(checker=ReversingChecker())
    def __rdivmod__(self: float, other: float) -> tuple[float, float]: ...

    @custom_function(checker=ReversingChecker())
    def __rfloordiv__(self: float, other: float) -> float: ...

    @custom_function(checker=ReversingChecker())
    def __rmod__(self: float, other: float) -> float: ...

    @custom_function(checker=ReversingChecker())
    def __rmul__(self: float, other: float) -> float: ...

    @hugr_op(float_op("fround"))  # TODO
    def __round__(self: float) -> float: ...

    @custom_function(checker=ReversingChecker())
    def __rpow__(self: float, other: float) -> float: ...

    @custom_function(checker=ReversingChecker())
    def __rsub__(self: float, other: float) -> float: ...

    @custom_function(checker=ReversingChecker())
    def __rtruediv__(self: float, other: float) -> float: ...

    @hugr_op(float_op("fsub"))
    def __sub__(self: float, other: float) -> float: ...

    @hugr_op(float_op("fdiv"))
    def __truediv__(self: float, other: float) -> float: ...

    @hugr_op(unsupported_op("trunc_s"))  # TODO `trunc_s` returns an option
    def __trunc__(self: float) -> float: ...


@custom_function(checker=DunderChecker("__abs__"), higher_order_value=False)
def abs(x): ...


# These should work equally well for signed integers if the need should arise
@hugr_op(
    external_op(
        "bytecast_int64_to_float64", args=[], ext=hugr.std.int.CONVERSIONS_EXTENSION
    )
)
def bytecast_nat_to_float(n: nat) -> float: ...


@hugr_op(
    external_op(
        "bytecast_float64_to_int64", args=[], ext=hugr.std.int.CONVERSIONS_EXTENSION
    )
)
def bytecast_float_to_nat(f: float) -> nat: ...


@custom_function(
    checker=DunderChecker("__divmod__", num_args=2), higher_order_value=False
)
def divmod(x, y): ...


@custom_function(checker=DunderChecker("__len__"), higher_order_value=False)
def len(x): ...


@custom_function(checker=DunderChecker("__pow__", num_args=2), higher_order_value=False)
def pow(x, y): ...


@custom_function(checker=DunderChecker("__round__"), higher_order_value=False)
def round(x): ...


# Delayed import to avoid cyclic import since `platform.result` overloads depend on
# types in `num`.
from guppylang.std.platform import panic  # noqa: E402
