"""Provides Python objects for builtin language keywords."""

from collections.abc import Callable, Generator
from typing import TYPE_CHECKING, Any, Generic, ParamSpec, Protocol, TypeVar

from guppylang_internals.error import GuppyComptimeError

T = TypeVar("T")

_MODIFIER_COMPTIME_ERROR = (
    "The `{modifier}` modifier is not supported in comptime functions"
)


class _Comptime:
    """Dummy class to support `@comptime` annotations and `comptime(...)` expressions"""

    def __call__(self, v: T) -> T:
        return v

    def __rmatmul__(self, other: Any) -> Any:
        # This method is to make the Python interpreter happy with @comptime at runtime
        return other


#: Function to tag compile-time evaluated Python expressions in a Guppy context.
#:
#: This function acts like the identity when execute in a Python context.
comptime = _Comptime()


#: Alias for `comptime` expressions
py = comptime


class _Owned:
    """Dummy class to support `@owned` annotations."""

    def __rmatmul__(self, other: Any) -> Any:
        return other


owned = _Owned()


#: The type of function values.
Fn = Callable  # type: ignore[type-arg]


class Copy(Protocol):
    """Bound to mark generic type parameters as being implicitly copyable."""


class Drop(Protocol):
    """Bound to mark generic type parameters as being implicitly droppable."""


def control(*args: Any, **kwargs: Any) -> Generator[None]:
    """Dummy function to support `with control(...):` blocks in Guppy code."""
    raise GuppyComptimeError(_MODIFIER_COMPTIME_ERROR.format(modifier="control"))


def dagger(*args: Any, **kwargs: Any) -> Generator[None]:
    """Dummy function to support `with dagger(...):` blocks in Guppy code."""
    raise GuppyComptimeError(_MODIFIER_COMPTIME_ERROR.format(modifier="dagger"))


def power(*args: Any, **kwargs: Any) -> Generator[None]:
    """Dummy function to support `with power(...):` blocks in Guppy code."""
    raise GuppyComptimeError(_MODIFIER_COMPTIME_ERROR.format(modifier="power"))


P = ParamSpec("P")
R = TypeVar("R")


class Unitary(Generic[P, R]):
    if TYPE_CHECKING:

        def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R: ...


class Daggerable(Generic[P, R]):
    if TYPE_CHECKING:

        def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R: ...


class Controllable(Generic[P, R]):
    if TYPE_CHECKING:

        def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R: ...
