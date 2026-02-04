"""Provides Python objects for builtin language keywords."""

from typing import Any, Protocol, TypeVar

T = TypeVar("T")


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


class Copy(Protocol):
    """Bound to mark generic type parameters as being implicitly copyable."""


class Drop(Protocol):
    """Bound to mark generic type parameters as being implicitly droppable."""
