"""Error handling with the `Result` type."""

from typing import Generic, no_type_check

from guppylang_internals.decorator import custom_function, custom_type
from guppylang_internals.definition.custom import NoopCompiler
from guppylang_internals.std._internal.compiler.either import (
    EitherConstructor,
    EitherTestCompiler,
    EitherUnwrapCompiler,
    either_to_hugr,
)
from guppylang_internals.tys.param import TypeParam

from guppylang import guppy
from guppylang.std.either import Either
from guppylang.std.lang import owned

T = guppy.type_var("T", copyable=False, droppable=False)
E = guppy.type_var("E", copyable=False, droppable=False)

_params = [TypeParam(0, "T", False, False), TypeParam(1, "E", False, False)]


@custom_type(either_to_hugr, params=_params)
class Result(Generic[T, E]):  # type: ignore[misc]
    """Represents a union of either an `ok(T)` or an `err(E)` value."""

    @custom_function(EitherTestCompiler(0))
    @no_type_check
    def is_ok(self: "Result[T, E]") -> bool:
        """Returns `True` for an `ok` value."""

    @custom_function(EitherTestCompiler(1))
    @no_type_check
    def is_err(self: "Result[T, E]") -> bool:
        """Returns `True` for an `err` value."""

    @custom_function(EitherUnwrapCompiler(0))
    @no_type_check
    def unwrap(self: "Result[T, E]" @ owned) -> T:
        """Returns the contained `ok` value, consuming `self`.

        Panics if `self` is an `err` value.
        """

    @custom_function(EitherUnwrapCompiler(1))
    @no_type_check
    def unwrap_err(self: "Result[T, E]" @ owned) -> E:
        """Returns the contained `err` value, consuming `self`.

        Panics if `self` is an `ok` value.
        """

    @custom_function(NoopCompiler())
    @no_type_check
    def into_either(self: "Result[T, E]" @ owned) -> Either[T, E]:
        """Casts a `Result` value into an `Either` value."""


@custom_function(EitherConstructor(0))
@no_type_check
def ok(val: T @ owned) -> Result[T, E]:
    """Constructs an `ok` result value."""


@custom_function(EitherConstructor(1))
@no_type_check
def err(err: E @ owned) -> Result[T, E]:
    """Constructs an `err` result value."""
