"""Union of two types.

Type `Either[L, R]` represents a value of either typr `L` ("left") or `R` ("right").
"""

from typing import Generic, no_type_check

from guppylang_internals.decorator import custom_function, custom_type
from guppylang_internals.std._internal.compiler.either import (
    EitherConstructor,
    EitherTestCompiler,
    EitherToOptionCompiler,
    EitherUnwrapCompiler,
    either_to_hugr,
)
from guppylang_internals.tys.param import TypeParam

from guppylang import guppy
from guppylang.std.lang import owned
from guppylang.std.option import Option

L = guppy.type_var("L", copyable=False, droppable=False)
R = guppy.type_var("R", copyable=False, droppable=False)
Droppable = guppy.type_var("Droppable", copyable=False, droppable=True)

_params = [TypeParam(0, "L", False, False), TypeParam(1, "L", False, False)]


@custom_type(either_to_hugr, params=_params)
class Either(Generic[L, R]):  # type: ignore[misc]
    """Represents a union of either a `left` or a `right` value."""

    @custom_function(EitherTestCompiler(0))
    @no_type_check
    def is_left(self: "Either[L, R]") -> bool:
        """Returns `True` for a `left` value."""

    @custom_function(EitherTestCompiler(1))
    @no_type_check
    def is_right(self: "Either[L, R]") -> bool:
        """Returns `True` for a `right` value."""

    @custom_function(EitherToOptionCompiler(0))
    @no_type_check
    def try_into_left(self: "Either[L, Droppable]" @ owned) -> Option[L]:
        """Returns the wrapped value if `self` is a `left` value, or `nothing`
        otherwise.

        This operation is only allowed if the `right` variant wraps a droppable type.
        """

    @custom_function(EitherToOptionCompiler(1))
    @no_type_check
    def try_into_right(self: "Either[Droppable, R]" @ owned) -> Option[R]:
        """Returns the wrapped value if `self` is a `right` value, or `nothing`
        otherwise.

        This operation is only allowed if the `left` variant wraps a droppable type.
        """

    @custom_function(EitherUnwrapCompiler(0))
    @no_type_check
    def unwrap_left(self: "Either[L, R]" @ owned) -> L:
        """Returns the contained `left` value, consuming `self`.

        Panics if `self` is a `right` value.
        """

    @custom_function(EitherUnwrapCompiler(1))
    @no_type_check
    def unwrap_right(self: "Either[L, R]" @ owned) -> R:
        """Returns the contained `right` value, consuming `self`.

        Panics if `self` is a `left` value.
        """


@custom_function(EitherConstructor(0))
@no_type_check
def left(val: L @ owned) -> Either[L, R]:
    """Constructs a `left` either value."""


@custom_function(EitherConstructor(1))
@no_type_check
def right(val: R @ owned) -> Either[L, R]:
    """Constructs a `right` either value."""
