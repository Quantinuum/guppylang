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

    To ensure static allocation, the maximum queue size must be specified in advance
    and is tracked in the type. For example, `Queue[int, 10]` is a queue that can
    hold at most 10 integers.

    Implemented as a circular buffer, giving O(1) push and pop.

    Use `empty_queue` to construct a new queue.
    """

    #: Underlying circular buffer holding the queue elements.
    #:
    #: Elements are stored contiguously from `self.start` up to and
    #: including `self.end`, wrapping around modulo MAX_SIZE.
    #:
    #: The `self.size` field tracks the number of elements currently
    #: in the queue, so we can distinguish between full and empty states.
    #: Without this, then the queue would be limited to MAX_SIZE - 1 since
    #: we cannot distinguish completely full and completely empty states
    #: with just using `self.start` and `self.end`.
    buf: array[Option[T], MAX_SIZE]  # type: ignore[valid-type, type-arg]
    #: Index of the current front of the queue (first element to be popped).
    start: int
    #: Index of the next free slot in `self.buf`.
    end: int
    #: Number of elements currently stored in the queue.
    size: int

    @guppy
    @no_type_check
    def __len__(self: Queue[T, MAX_SIZE]) -> int:
        """Returns the number of elements currently stored in the queue."""
        return self.size

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
        if self.size >= MAX_SIZE:
            panic("Queue.push: max size reached")
        self.buf[self.end].swap(some(elem)).unwrap_nothing()
        new_end = (self.end + 1) % MAX_SIZE
        return Queue(self.buf, self.start, new_end, self.size + 1)

    @guppy
    @no_type_check
    def pop(self: Queue[T, MAX_SIZE] @ owned) -> tuple[T, Queue[T, MAX_SIZE]]:
        """
        Removes the next element from the queue and returns it.

        Panics if the queue is empty.
        """
        if self.size == 0:
            panic("Queue.pop: queue is empty")
        elem = self.buf[self.start].take().unwrap()
        new_start = (self.start + 1) % MAX_SIZE
        return elem, Queue(self.buf, new_start, self.end, self.size - 1)

    @guppy
    @no_type_check
    def peek(
        self: Queue[TCopyable, MAX_SIZE] @ owned,
    ) -> tuple[TCopyable, Queue[TCopyable, MAX_SIZE]]:
        """Returns a copy of the top element of the queue without removing it.

        Panics if the queue is empty.

        Note that this operation is only allowed if the queue elements are copyable.
        """
        if self.size == 0:
            panic("Queue.peek: queue is empty")
        elem = self.buf[self.start].unwrap()
        return elem, Queue(self.buf, self.start, self.end, self.size)

    @guppy
    @no_type_check
    def discard_empty(self: Queue[T, MAX_SIZE] @ owned) -> None:
        """Discards a queue of potentially non-droppable elements assuming that the
        queue is empty.

        Panics if the queue is not empty.
        """
        if self.size != 0:
            panic("Queue.discard_empty: queue is not empty")
        for elem in self.buf:
            elem.unwrap_nothing()


@guppy
@no_type_check
def empty_queue() -> Queue[T, MAX_SIZE]:
    """Constructs a new empty queue."""
    buf = array(nothing[T]() for _ in range(MAX_SIZE))
    return Queue(buf, 0, 0, 0)
