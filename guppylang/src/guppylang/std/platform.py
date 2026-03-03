"""Platform functions."""

# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def"

from __future__ import annotations

from typing import TYPE_CHECKING, no_type_check

from guppylang_internals.decorator import custom_function
from guppylang_internals.nodes import AbortKind
from guppylang_internals.std._internal.checker import (
    AbortChecker,
    BarrierChecker,
)
from guppylang_internals.std._internal.compiler.platform import (
    ArrayResultCompiler,
    ResultCompiler,
)
from guppylang_internals.tys.builtin import int_type, string_type
from guppylang_internals.tys.ty import FuncInput, FunctionType, InputFlags, NoneType

from guppylang import guppy

if TYPE_CHECKING:
    from guppylang.std.array import array
    from guppylang.std.lang import comptime
    from guppylang.std.num import nat

n = guppy.nat_var("n")


@custom_function(ResultCompiler("result_int", with_int_width=True))
def _result_int(tag: str @ comptime, value: int) -> None: ...


@custom_function(ResultCompiler("result_uint", with_int_width=True))
def _result_nat(tag: str @ comptime, value: nat) -> None: ...


@custom_function(ResultCompiler("result_bool"))
def _result_bool(tag: str @ comptime, value: bool) -> None: ...


@custom_function(ResultCompiler("result_f64"))
def _result_float(tag: str @ comptime, value: float) -> None: ...


@custom_function(ArrayResultCompiler("result_array_int", with_int_width=True))
def _result_int_array(tag: str @ comptime, value: array[int, n]) -> None: ...


@custom_function(ArrayResultCompiler("result_array_uint", with_int_width=True))
def _result_nat_array(tag: str @ comptime, value: array[nat, n]) -> None: ...


@custom_function(ArrayResultCompiler("result_array_bool"))
def _result_bool_array(tag: str @ comptime, value: array[bool, n]) -> None: ...


@custom_function(ArrayResultCompiler("result_array_f64"))
def _result_float_array(tag: str @ comptime, value: array[float, n]) -> None: ...


@guppy.overload(
    _result_int,
    _result_nat,
    _result_bool,
    _result_float,
    _result_int_array,
    _result_nat_array,
    _result_bool_array,
    _result_float_array,
)
def result(tag: str, value):
    """Report a result with the given tag and value.

    This is the primary way to report results from the program back to the user.
    On Quantinuum systems a single shot execution will return a list of pairs of
    (tag, value).

    Args:
        tag: The tag of the result. Must be a string literal
        value: The value of the result. Currently supported value types are `int`,
        `nat`, `float`, and `bool`.
    """


@custom_function(
    checker=AbortChecker(AbortKind.Panic),
    higher_order_value=False,
    # We need to define a signature manually here for error reporting purposes. This is
    # because we are using a custom checker due to the arbitrary extra inputs that
    # can't be represented by a standard Guppy signature.
    signature=FunctionType(
        [
            FuncInput(string_type(), InputFlags.NoFlags, "msg"),
        ],
        NoneType(),
    ),
    has_var_args=True,
)
def _panic(msg: str, *args) -> None: ...


@custom_function(
    checker=AbortChecker(AbortKind.Panic),
    higher_order_value=False,
    signature=FunctionType(
        [
            FuncInput(string_type(), InputFlags.NoFlags, "msg"),
            FuncInput(int_type(), InputFlags.NoFlags, "signal"),
        ],
        NoneType(),
    ),
    has_var_args=True,
)
def _panic_with_signal(msg: str, signal: int, *args) -> None: ...


@guppy.overload(_panic, _panic_with_signal)
def panic(msg: str, signal: int = 1, *args):
    """Panic, throwing an error with the given message (and signal if given), and
    immediately exit the program, aborting any subsequent shots.

    If the first value after the message is an integer, it is treated as the signal.
    Therefore, an integer cannot be the first extra input unless a signal is provided.
    Since extra inputs are meant to be linear values, integers shouldn't be passed as
    extra inputs anyway.

    Return type is arbitrary, as this function never returns.

    On Quantinuum systems only signals in the range 1<=signal<=1000 are supported.

    Args:
        message: The message to display. Must be a string literal.
        signal: An optional integer for distinguishing different failure modes.
        args: Arbitrary extra inputs, will not affect the message. Only useful for
        consuming linear values.
    """


@custom_function(
    checker=AbortChecker(AbortKind.ExitShot),
    higher_order_value=False,
    # We need to define a signature manually here for error reporting purposes. This is
    # because we are using a custom checker due to the arbitrary extra inputs that
    # can't be represented by a standard Guppy signature.
    signature=FunctionType(
        [
            FuncInput(string_type(), InputFlags.NoFlags, "message"),
        ],
        NoneType(),
    ),
    has_var_args=True,
)
def _exit(msg: str, *args) -> None: ...


@custom_function(
    checker=AbortChecker(AbortKind.ExitShot),
    higher_order_value=False,
    signature=FunctionType(
        [
            FuncInput(string_type(), InputFlags.NoFlags, "message"),
            FuncInput(int_type(), InputFlags.NoFlags, "signal"),
        ],
        NoneType(),
    ),
    has_var_args=True,
)
def _exit_with_signal(msg: str, signal: int, *args) -> None: ...


@guppy.overload(_exit, _exit_with_signal)
def exit(msg: str, signal: int = 1, *args):
    """Exit, reporting the given message (and signal if given), and immediately exit the
    program. Subsequent shots may still run.

    If the first value after the message is an integer, it is treated as the signal.
    Therefore, an integer cannot be the first extra input unless a signal is provided.
    Since extra inputs are meant to be linear values, integers shouldn't be passed as
    extra inputs anyway.

    Return type is arbitrary, as this function never returns.

    On Quantinuum systems only signals in the range 1<=signal<=1000 are supported.

    Args:
        message: The message to display. Must be a string literal.
        signal: An optional integer for distinguishing different failure modes.
        args: Arbitrary extra inputs, will not affect the message. Only useful for
        consuming linear values.
    """


@custom_function(checker=BarrierChecker(), higher_order_value=False)
@no_type_check
def barrier(*args) -> None:
    """Barrier to guarantee that all operations before the barrier are completed before
    operations after the barrier are started."""
