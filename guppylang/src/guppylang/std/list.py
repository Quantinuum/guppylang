"""EXPERIMENTAL: The `list` type"""

# ruff: noqa: E501
# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def, type-arg"

from __future__ import annotations

from typing import TYPE_CHECKING

from guppylang_internals.decorator import custom_function, extend_type
from guppylang_internals.std._internal.checker import UnsupportedChecker
from guppylang_internals.std._internal.compiler.list import (
    ListDiscardEmptyCompiler,
    ListGetitemCompiler,
    ListIterCompiler,
    ListLengthCompiler,
    ListNextCompiler,
    ListPopCompiler,
    ListPushCompiler,
    ListSetitemCompiler,
    ListSwapCompiler,
)
from guppylang_internals.tys import Effect
from guppylang_internals.tys.builtin import list_type_def

from guppylang import guppy
from guppylang.std.option import Option  # noqa: TC001

if TYPE_CHECKING:
    from guppylang.std.lang import owned


T = guppy.type_var("T", copyable=True, droppable=False)
D = guppy.type_var("D", copyable=False, droppable=True)
L = guppy.type_var("L", copyable=False, droppable=False)


@extend_type(list_type_def)
class list[T]:
    """Mutable sequence of items with a single element type.

    Lists cannot be copied, even when their elements can be copied. Assigning or
    passing a list by ownership moves it; the previous owner cannot use it again.
    Access and mutation methods borrow the list and return its updated handle to
    the caller. ``discard_empty`` consumes the list by ownership.
    To append a value read from the same list, compute the value before calling
    ``append`` so the two operations do not borrow the list simultaneously.

    Elements are stored directly, including noncopyable elements. Indexed reads
    require copyable elements. Noncopyable elements can be moved out by ``pop``
    or consuming iteration. Ordinary assignment requires droppable elements
    because its result is None and it disposes of the replaced value.
    ``swap`` transfers the replaced element back to the caller and accepts any
    element type.

    A list may be implicitly discarded only when its elements are droppable.
    Cleanup consumes its elements before releasing the empty list.

    Iteration consumes the list and yields its elements in insertion order. To
    inspect a borrowed list of copyable elements, iterate over ``range(len(xs))``
    and access ``xs[i]``. A consumed list cannot be iterated again.
    """

    @custom_function(ListGetitemCompiler(), effects=[Effect.ANY])
    def __getitem__(self: list[T], idx: int) -> T: ...

    @custom_function(ListSetitemCompiler(), effects=[Effect.ANY])
    def __setitem__(self: list[D], idx: int, value: D @ owned) -> None: ...

    @custom_function(ListSwapCompiler(), effects=[Effect.ANY])
    def swap(self: list[L], idx: int, replacement: L @ owned) -> L:
        """Replace the indexed element and return the prior element by ownership.

        The list length and element order are unchanged. Panic if the index is
        out of bounds. The caller must consume a returned nondroppable element.
        """

    @custom_function(ListLengthCompiler())
    def __len__(self: list[L]) -> int: ...

    @custom_function(checker=UnsupportedChecker(), higher_order_value=False)
    def __new__(x): ...

    @custom_function(ListIterCompiler(), effects=[Effect.ANY])
    def __iter__(self: list[L] @ owned) -> list[L]: ...

    @custom_function(ListNextCompiler(), effects=[Effect.ANY])
    def __next__(self: list[L] @ owned) -> Option[tuple[L, list[L]]]: ...

    @custom_function(ListPushCompiler())
    def append(self: list[L], item: L @ owned) -> None: ...

    @custom_function(ListPopCompiler(), effects=[Effect.ANY])  # panics if list empty
    def pop(self: list[L]) -> L: ...

    @custom_function(ListDiscardEmptyCompiler(), effects=[Effect.ANY])
    def discard_empty(self: list[L] @ owned) -> None:
        """Consume an empty list. Panic if the list is nonempty.

        This accepts any element type, including nondroppable elements. Removing
        all elements with ``pop`` makes the list empty.
        """
