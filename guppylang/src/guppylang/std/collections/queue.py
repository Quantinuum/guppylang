from __future__ import annotations

from typing import TYPE_CHECKING, Generic, no_type_check

from guppylang.decorator import guppy
from guppylang.std.array import array
from guppylang.std.option import Option, nothing, some
from guppylang.std.platform import panic

if TYPE_CHECKING:
    from guppylang.std.lang import owned

T = guppy.type_var("T", copyable=False, droppable=False)
TCopyable = guppy.type_var("TCopyable", copyable=True, droppable=False)
MAX_SIZE = guppy.nat_var("MAX_SIZE")


@guppy.struct
class Queue(Generic[T, MAX_SIZE]):  # type: ignore[misc]
    """A first-in-first-out (FIFO) growable collection of values.

    To ensure static allocation, the maximum queue size must be specified in advance and
    is tracked in the type. For example, the `Queue[int, 10]` is a queue that can hold
    at most 10 integers.

    Use `empty_queue` to construct a new queue.
    """

    #: Underlying buffer holding the queue elements.
    #:
    #: INVARIANT: All array elements up to and including index `self.end - 1` are
    #: `option.some` variants and all further ones are `option.nothing`.
    buf: array[Option[T], MAX_SIZE]  # type: ignore[valid-type, type-arg]

    #: Index of the next free index in `self.buf`.
    end: int

    @guppy
    @no_type_check
    def __len__(self: Queue[T, MAX_SIZE]) -> int:
        """Returns the number of elements currently stored in the queue."""
        return self.end

    @guppy
    @no_type_check
    def __iter__(self: Queue[T, MAX_SIZE] @ owned) -> Queue[T, MAX_SIZE]:
        """Returns an iterator over the elements in the queue from bottom to top."""
        return self

    @guppy
    @no_type_check
    def __next__(
        self: Queue[T, MAX_SIZE] @ owned,
    ) -> Option[tuple[T, Queue[T, MAX_SIZE]]]:
        if len(self) == 0:
            self.discard_empty()
            return nothing()
        val, new_queue = self.pop()
        return some((val, new_queue))

    @guppy
    @no_type_check
    def push(self: Queue[T, MAX_SIZE] @ owned, elem: T @ owned) -> Queue[T, MAX_SIZE]:
        """Adds an element to the end of the queue.

        Panics if the queue has already reached its maximum size.
        """
        if self.end >= MAX_SIZE:
            panic("Queue.push: max size reached")
        self.buf[self.end].swap(some(elem)).unwrap_nothing()
        return Queue(self.buf, self.end + 1)

    @guppy
    @no_type_check
    def pop(self: Queue[T, MAX_SIZE] @ owned) -> tuple[T, Queue[T, MAX_SIZE]]:
        """
        Removes the next element from the queue and returns it.

        Panics if the queue is empty.
        """
        if self.end <= 0:
            panic("Queue.pop: queue is empty")
        elem = self.buf[0].take().unwrap()
        for i in range(self.end - 1):
            next_elem = self.buf[i + 1].take().unwrap()
            self.buf[i].swap(some(next_elem)).unwrap_nothing()
        return elem, Queue(self.buf, self.end - 1)

    @guppy
    @no_type_check
    def peek(
        self: Queue[TCopyable, MAX_SIZE] @ owned,
    ) -> tuple[TCopyable, Queue[TCopyable, MAX_SIZE]]:
        """Returns a copy of the top element of the queue without removing it.

        Panics if the queue is empty.

        Note that this operation is only allowed if the queue elements are copyable.
        """
        if self.end <= 0:
            panic("Queue.peek: queue is empty")
        elem = self.buf[0].unwrap()
        return elem, Queue(self.buf, self.end)

    @guppy
    @no_type_check
    def discard_empty(self: Queue[T, MAX_SIZE] @ owned) -> None:
        """Discards a queue of potentially non-droppable elements assuming that the
        queue is empty.

        Panics if the queue is not empty.
        """
        if self.end > 0:
            panic("Queue.discard_empty: queue is not empty")
        for elem in self.buf:
            elem.unwrap_nothing()


@guppy
@no_type_check
def empty_queue() -> Queue[T, MAX_SIZE]:
    """Constructs a new empty queue."""
    buf = array(nothing[T]() for _ in range(MAX_SIZE))
    return Queue(buf, 0)
