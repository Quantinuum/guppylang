from guppylang import guppy
from guppylang.std.collections import (
    Stack,
    empty_stack,
    PriorityQueue,
    empty_priority_queue,
)


def test_stack(run_int_fn) -> None:
    @guppy
    def main() -> int:
        stack: Stack[int, 10] = empty_stack()
        for i in range(10):
            stack = stack.push(i)
        s = 0
        i = 1
        while len(stack) > 0:
            x, stack = stack.pop()
            s += x * i
            i += 1
        stack.discard_empty()
        return s

    run_int_fn(
        main,
        # multiplier * value for ordered values in the stack
        sum((i + 1) * x for i, x in enumerate(reversed(list(range(10))))),
    )


def test_stack_iter(run_int_fn) -> None:
    @guppy
    def main() -> int:
        stack: Stack[int, 10] = empty_stack()
        for i in range(10):
            stack = stack.push(i)
        s = 0
        i = 1
        for x in stack:
            s += x * i
            i += 1
        return s

    run_int_fn(
        main,
        # multiplier * value for ordered values in the stack
        sum((i + 1) * x for i, x in enumerate(reversed(list(range(10))))),
    )


def test_priority_queue(run_int_fn) -> None:
    @guppy
    def main() -> int:
        pq: PriorityQueue[int, 10] = empty_priority_queue()
        for i in range(10):
            # values are in order, priority is reversed
            pq = pq.push(i, 9 - i)
        s = 0
        multiplier = 1
        while len(pq) > 0:
            _priority, value, pq = pq.pop()
            # use multiplier to ensure the correct order
            s += value * multiplier
            multiplier += 1
        pq.discard_empty()
        return s

    run_int_fn(
        main,
        # multiplier * value for ordered values in priority queue
        sum((m + 1) * v for m, v in enumerate(reversed(list(range(10))))),
    )


def test_priority_queue_iter(run_int_fn) -> None:
    @guppy
    def main() -> int:
        pq: PriorityQueue[int, 10] = empty_priority_queue()
        for i in range(10):
            # values are in order, priority is reversed
            pq = pq.push(i, 9 - i)
        s = 0
        multiplier = 1
        for priority, value in pq:
            # use multiplier to ensure the correct order
            s += value * multiplier
            multiplier += 1
        return s

    run_int_fn(
        main,
        # multiplier * value for ordered values in priority queue
        sum((m + 1) * v for m, v in enumerate(reversed(list(range(10))))),
    )
