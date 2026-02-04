"""Mocks for a number of builtin functions to be used during tracing.

For example, the builtin `int(x)` function tries calling `x.__int__()` and raises a
`TypeError` if this call doesn't return an `int`. During tracing however, we also want
to allow `int(x)` if `x` is an abstract `GuppyObject`. To allow this, we need to mock
the builtins to avoid raising the `TypeError` in that case.
"""

import builtins
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from guppylang_internals.tracing.object import GuppyObject, GuppyStructObject


def _mock_meta(cls: type) -> type:
    """Returns a metaclass that replicates the behaviour of the provided class.

    The only way to distinguishing a `_mock_meta(T)` from an actual `T` is via checking
    reference equality using the `is` operator.
    """

    class MockMeta(type):
        def __instancecheck__(self, instance: Any) -> bool:
            return cls.__instancecheck__(instance)

        def __subclasscheck__(self, subclass: type) -> bool:
            return cls.__subclasscheck__(subclass)

        def __eq__(self, other: object) -> Any:
            return other == cls

        def __ne__(self, other: object) -> Any:
            return other != cls

    MockMeta.__name__ = type.__name__
    MockMeta.__qualname__ = type.__qualname__
    return MockMeta


class float(builtins.float, metaclass=_mock_meta(builtins.float)):  # type: ignore[metaclass]
    def __new__(cls, x: Any = 0.0, /) -> Any:
        if isinstance(x, GuppyObject):
            return x.__float__()
        return builtins.float(x)


class int(builtins.int, metaclass=_mock_meta(builtins.int)):  # type: ignore[metaclass]
    def __new__(cls, x: Any = 0, /, *args: Any, **kwargs: Any) -> Any:
        if isinstance(x, GuppyObject):
            return x.__int__(*args, **kwargs)
        return builtins.int(x, *args, **kwargs)


def len(x: Any) -> Any:
    if isinstance(x, GuppyObject | GuppyStructObject):
        return x.__len__()
    return builtins.len(x)


@contextmanager
def mock_builtins(f: Callable[..., Any]) -> Iterator[None]:
    # References to builtins inside `f` are looked up in `f.__builtins__`.
    # Unfortunately, this is a readonly attribute so we can't assign a new dict to it.
    # Mutating in-place is also a bad idea since this would also mutate the `builtins`
    # module, making us loose an escape hatch to query the original. Instead, let's
    # mutate `f.__globals__` which makes Python believe that the builtins are shadowed.
    mock = {"float": float, "int": int, "len": len}
    old = {x: f.__globals__[x] for x in mock if x in f.__globals__}
    f.__globals__.update(mock)
    try:
        yield
    finally:
        # Reset back to the prior state since mutating `f.__globals__` also mutated the
        # outer globals
        for x in mock:
            if x not in old:
                del f.__globals__[x]
        f.__globals__.update(old)
