from __future__ import annotations

from typing import Generic, no_type_check

from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned, panic
from guppylang.std.option import Option, nothing, some

T = guppy.type_var("T", copyable=False, droppable=False)
TCopyable = guppy.type_var("TCopyable", copyable=True, droppable=False)
MAX_SIZE = guppy.nat_var("MAX_SIZE")


@guppy.struct
class PriorityQueue(Generic[T, MAX_SIZE]):  # type: ignore[misc]
    """A queue of values ordered by priority.

    Values with the lowest priority value will be popped from the queue first.
    (e.g. Priority 1 will be returned before priority 2.) To ensure static
    allocation, the maximum queue size must be specified in advance and
    is tracked in the type. For example, the `PriorityQueue[int, 10]`
    is a queue that can hold at most 10 prioritized integers.

    Use `empty_priority_queue` to construct a new priority_queue.
    """

    #: Underlying buffer holding the priority queue elements.
    #:
    #: INVARIANT: All array elements up to and including index `self.size - 1` are
    #: `option.some` variants and all further ones are `option.nothing`.
    buf: array[Option[tuple[int, T]], MAX_SIZE]  # type: ignore[valid-type, type-arg]

    #: Index of the next free index in `self.buf`.
    size: int

    @guppy
    @no_type_check
    def __len__(self: PriorityQueue[T, MAX_SIZE]) -> int:
        """Returns the number of elements currently stored in the priority queue."""
        return self.size

    @guppy
    @no_type_check
    def __iter__(
        self: PriorityQueue[T, MAX_SIZE] @ owned,
    ) -> PriorityQueue[T, MAX_SIZE]:
        """Returns an iterator over the queued elements paired with their priority.

        Elements are yielded in priority order.
        """
        return self

    @guppy
    @no_type_check
    def __next__(
        self: PriorityQueue[T, MAX_SIZE] @ owned,
    ) -> Option[tuple[tuple[int, T], PriorityQueue[T, MAX_SIZE]]]:
        if len(self) == 0:
            self.discard_empty()
            return nothing()
        prio, val, new_queue = self.pop()
        return some(((prio, val), new_queue))

    @guppy
    @no_type_check
    def push(
        self: PriorityQueue[T, MAX_SIZE] @ owned,
        value: T @ owned,
        priority: int,
    ) -> PriorityQueue[T, MAX_SIZE]:
        """Adds an element in the correct order to the priority queue.

        Panics if the priority queue has already reached its maximum size.
        """
        if self.size >= MAX_SIZE:
            panic("PriorityQueue.push: max size reached")
        self.buf[self.size].swap(some((priority, value))).unwrap_nothing()
        i = self.size
        while i > 0:
            parent_i = (i - 1) // 2
            prio, val = self.buf[i].take().unwrap()
            parent_prio, parent_val = self.buf[parent_i].take().unwrap()
            if prio >= parent_prio:
                self.buf[i].swap(some((prio, val))).unwrap_nothing()
                self.buf[parent_i].swap(
                    some((parent_prio, parent_val))
                ).unwrap_nothing()
                break
            self.buf[i].swap(some((parent_prio, parent_val))).unwrap_nothing()
            self.buf[parent_i].swap(some((prio, val))).unwrap_nothing()
            i = parent_i
        return PriorityQueue(self.buf, self.size + 1)

    @guppy
    @no_type_check
    def pop(
        self: PriorityQueue[T, MAX_SIZE] @ owned,
    ) -> tuple[int, T, PriorityQueue[T, MAX_SIZE]]:
        """Removes the next element from the priority queue.

        Panics if the priority queue is empty.
        """
        if self.size <= 0:
            panic("PriorityQueue.pop: priority queue is empty")
        return_prio, return_val = self.buf[0].take().unwrap()
        new_size = self.size - 1
        if new_size == 0:
            return return_prio, return_val, PriorityQueue(self.buf, new_size)
        displaced_prio, displaced_val = self.buf[new_size].take().unwrap()
        i = 0
        while True:
            left_i = 2 * i + 1
            if left_i >= new_size:
                break
            right_i = left_i + 1
            if right_i < new_size:
                left_elem = self.buf[left_i].take().unwrap()
                right_elem = self.buf[right_i].take().unwrap()
                left_prio, left_val = left_elem
                right_prio, right_val = right_elem
                if right_prio < left_prio:
                    child_i, child_prio, child_val = right_i, right_prio, right_val
                    self.buf[left_i].swap(some((left_prio, left_val))).unwrap_nothing()
                else:
                    child_i, child_prio, child_val = left_i, left_prio, left_val
                    self.buf[right_i].swap(
                        some((right_prio, right_val))
                    ).unwrap_nothing()
            else:
                left_elem = self.buf[left_i].take().unwrap()
                child_prio, child_val = left_elem
                child_i = left_i
            if displaced_prio <= child_prio:
                self.buf[child_i].swap(some((child_prio, child_val))).unwrap_nothing()
                break
            self.buf[i].swap(some((child_prio, child_val))).unwrap_nothing()
            i = child_i
        self.buf[i].swap(some((displaced_prio, displaced_val))).unwrap_nothing()
        return return_prio, return_val, PriorityQueue(self.buf, new_size)

    @guppy
    @no_type_check
    def peek(
        self: PriorityQueue[TCopyable, MAX_SIZE] @ owned,
    ) -> tuple[int, TCopyable, PriorityQueue[TCopyable, MAX_SIZE]]:
        """Returns a copy of the next element in the priority queue without removing it.

        Panics if the priority queue is empty.

        Note that this operation is only allowed if the priority queue elements are
        copyable.
        """
        if self.size <= 0:
            panic("PriorityQueue.peek: priority queue is empty")
        prio, val = self.buf[0].unwrap()
        return prio, val, PriorityQueue(self.buf, self.size)

    @guppy
    @no_type_check
    def discard_empty(self: PriorityQueue[T, MAX_SIZE] @ owned) -> None:
        """Discards a priority queue of potentially non-droppable elements assuming that
        the queue is empty.

        Panics if the queue is not empty.
        """
        if self.size > 0:
            panic("PriorityQueue.discard_empty: priority queue is not empty")
        for elem in self.buf:
            elem.unwrap_nothing()


@guppy
@no_type_check
def empty_priority_queue() -> PriorityQueue[T, MAX_SIZE]:
    """Constructs a new empty priority queue."""
    buf = array(nothing[tuple[int, T]]() for _ in range(MAX_SIZE))  # type: ignore[valid-type]
    return PriorityQueue(buf, 0)
