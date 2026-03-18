from guppylang import guppy
from guppylang.std.collections import (
    Stack,
    empty_stack,
    PriorityQueue,
    empty_priority_queue,
    Queue,
    empty_queue,
)
import pytest
from guppylang.emulator import EmulatorError


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


def test_queue(run_int_fn) -> None:
    @guppy
    def main() -> int:
        queue: Queue[int, 10] = empty_queue()
        for i in range(10):
            queue = queue.push(i)
        s = 0
        i = 1
        while len(queue) > 0:
            x, queue = queue.pop()
            s += x * i
            i += 1
        queue.discard_empty()
        return s

    run_int_fn(
        main,
        # multiplier * value for ordered values in the queue
        sum((i + 1) * x for i, x in enumerate(list(range(10)))),
    )


def test_queue_iter(run_int_fn) -> None:
    @guppy
    def main() -> int:
        queue: Queue[int, 10] = empty_queue()
        for i in range(10):
            queue = queue.push(i)
        s = 0
        i = 1
        for x in queue:
            s += x * i
            i += 1
        return s

    run_int_fn(
        main,
        # multiplier * value for ordered values in the queue
        sum((i + 1) * x for i, x in enumerate(list(range(10)))),
    )


def test_queue_full() -> None:
    @guppy
    def main() -> None:
        queue: Queue[int, 1] = empty_queue()
        for i in range(2):
            queue = queue.push(i)

        queue.discard_empty()

    with pytest.raises(
        EmulatorError, match=r"Panic \(#1001\): Queue.push: max size reached"
    ):
        main.emulator(n_qubits=0).stabilizer_sim().with_seed(42).run()


def test_queue_empty() -> None:
    @guppy
    def main() -> None:
        queue: Queue[int, 1] = empty_queue()
        for i in range(1):
            queue = queue.push(i)

        for _ in range(2):
            _, queue = queue.pop()

        queue.discard_empty()

    with pytest.raises(
        EmulatorError, match=r"Panic \(#1001\): Queue.pop: queue is empty"
    ):
        main.emulator(n_qubits=0).stabilizer_sim().with_seed(42).run()
