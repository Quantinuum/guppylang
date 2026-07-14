from __future__ import annotations

from typing import TYPE_CHECKING, Self, no_type_check

from guppylang_internals.std._internal.moved import (
    produce_moved_class,
    produce_moved_function,
)

from guppylang.decorator import guppy
from guppylang.std.array import array
from guppylang.std.num import nat
from guppylang.std.option import Option, nothing, some
from guppylang.std.platform import panic

if TYPE_CHECKING:
    from guppylang.std.lang import owned


@guppy.struct
class Stack[T, MAX_SIZE: nat]:
    """A last-in-first-out (LIFO) growable collection of values.

    To ensure static allocation, the maximum stack size must be specified in advance and
    is tracked in the type. For example, the `Stack[int, 10]` is a stack that can hold
    at most 10 integers.

    Use `empty_stack` to construct a new stack.
    """

    #: Underlying buffer holding the stack elements.
    #:
    #: INVARIANT: All array elements up to and including index `self._end - 1` are
    #: `option.some` variants and all further ones are `option.nothing`.
    _buf: array[Option[T], MAX_SIZE]

    #: Index of the next free index in `self._buf`.
    _end: int

    @guppy
    @no_type_check
    def __len__(self) -> int:
        """Returns the number of elements currently stored in the stack."""
        return self._end

    @guppy
    @no_type_check
    def __iter__(self: Self @ owned) -> Self:
        """Returns an iterator over the elements in the stack from top to bottom."""
        return self

    @guppy
    @no_type_check
    def __next__(self: Self @ owned) -> Option[tuple[T, Self]]:
        if len(self) == 0:
            self.discard_empty()
            return nothing()
        val = self.pop()
        return some((val, self))

    @guppy
    @no_type_check
    def push(self, elem: T @ owned) -> None:
        """Adds an element to the top of the stack.

        Panics if the stack has already reached its maximum size.
        """
        if self._end >= MAX_SIZE:  # type: ignore[misc]
            panic("Stack.push: max size reached")
        self._buf[self._end].swap(some(elem)).unwrap_nothing()
        self._end += 1

    @guppy
    @no_type_check
    def pop(self) -> T:
        """
        Removes the top element from the stack and returns it.

        Panics if the stack is empty.
        """
        if self._end <= 0:
            panic("Stack.pop: stack is empty")
        elem = self._buf[self._end - 1].take().unwrap()
        self._end -= 1
        return elem

    @guppy
    @no_type_check
    def peek[TC: Copy](self: Stack[TC, MAX_SIZE] @ owned) -> TC:
        """Returns a copy of the top element of the stack without removing it.

        Panics if the stack is empty.

        Note that this operation is only allowed if the stack elements are copyable.
        """
        if self._end <= 0:
            panic("Stack.peek: stack is empty")
        return self._buf[self._end - 1].unwrap()

    @guppy
    @no_type_check
    def discard_empty(self: Stack[T, MAX_SIZE] @ owned) -> None:
        """Discards a stack of potentially non-droppable elements assuming that the
        stack is empty.

        Panics if the stack is not empty.
        """
        if self._end > 0:
            panic("Stack.discard_empty: stack is not empty")
        for elem in self._buf:
            elem.unwrap_nothing()


@guppy
@no_type_check
def empty_stack[T, MAX_SIZE: nat]() -> Stack[T, MAX_SIZE]:
    """Constructs a new empty stack."""
    buf = array(nothing[T]() for _ in range(MAX_SIZE))  # type: ignore[name-defined]
    return Stack(buf, 0)


# TODO remove once https://github.com/Quantinuum/guppylang/issues/1019 has been resolved
#  for a while
PriorityQueue = produce_moved_class(
    "guppylang.std.collections.stack",
    "PriorityQueue",
    "guppylang.std.collections.priority_queue",
)
empty_priority_queue = produce_moved_function(  # type: ignore[var-annotated]
    "guppylang.std.collections.stack",
    "empty_priority_queue",
    "guppylang.std.collections.priority_queue",
)
