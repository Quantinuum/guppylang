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


def test_priority_queue_repeated_push_pop(run_int_fn) -> None:
    @guppy
    def main() -> int:
        pq: PriorityQueue[int, 5] = empty_priority_queue()
        # Fill to capacity using priorities equal to values.
        for i in range(5):
            pq = pq.push(i, i)
        # Pop twice, then push a couple more values after freeing space.
        _, _, pq = pq.pop()
        _, _, pq = pq.pop()
        for i in range(5, 7):
            pq = pq.push(i, i)
        # Pop twice again and then push more values to exercise repeated cycles.
        _, _, pq = pq.pop()
        _, _, pq = pq.pop()
        for i in range(7, 9):
            pq = pq.push(i, i)
        # Drain remaining values in priority order and verify they are still ordered.
        total = 0
        multiplier = 1
        while len(pq) > 0:
            _, value, pq = pq.pop()
            total += value * multiplier
            multiplier += 1
        pq.discard_empty()
        return total

    run_int_fn(main, sum((m + 1) * v for m, v in enumerate(range(4, 9))))


def test_queue(run_int_fn) -> None:
    """Tests that the queue maintains FIFO order when popping elements."""

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
    """Tests that queue iteration yields elements in FIFO order."""

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


def test_queue_full(run_int_fn) -> None:
    """Tests that a queue can be filled to its maximum capacity."""

    @guppy
    def main() -> int:
        queue: Queue[int, 5] = empty_queue()
        for i in range(5):
            queue = queue.push(i)
        return len(queue)

    run_int_fn(main, 5)


def test_queue_beyond_full() -> None:
    """Tests that pushing beyond the queue's maximum capacity raises a panic."""

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
    """Tests that popping from an empty queue raises a panic."""

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


def test_queue_beyond_max_size(run_int_fn) -> None:
    """Tests that the queue maintains FIFO order during push/pop
    sequences that cause multiple slot reuses and wraparounds."""

    @guppy
    def main() -> int:
        q: Queue[int, 5] = empty_queue()
        for i in range(4):
            q = q.push(i)

        for _ in range(2):
            _, q = q.pop()

        for i in range(4, 6):
            q = q.push(i)
        _, q = q.pop()
        q = q.push(6)
        _, q = q.pop()
        q = q.push(7)
        _, q = q.pop()
        q = q.push(8)
        _, q = q.pop()
        q = q.push(9)
        total = 0
        multiplier = 1

        while len(q) > 0:
            x, q = q.pop()
            total += x * multiplier
            multiplier += 1
        q.discard_empty()
        return total

    run_int_fn(main, 6 * 1 + 7 * 2 + 8 * 3 + 9 * 4)


def test_queue_wraparound_len(run_int_fn) -> None:
    """Tests that the queue length is accurate after operations that
    cause internal slots to be reused."""

    @guppy
    def main() -> int:
        q: Queue[int, 5] = empty_queue()
        for i in range(3):
            q = q.push(i)
        for _ in range(2):
            _, q = q.pop()
        for i in range(3, 5):
            q = q.push(i)
        return len(q)

    run_int_fn(main, 3)


def test_queue_wraparound_iter(run_int_fn) -> None:
    """Tests that the queue maintains insertion order even when
    usage causes internal slots to be reused."""

    @guppy
    def main() -> int:
        q: Queue[int, 5] = empty_queue()
        for i in range(3):
            q = q.push(i)
        for _ in range(2):
            _, q = q.pop()
        for i in range(3, 5):
            q = q.push(i)
        total = 0
        multiplier = 1
        for x in q:
            total += x * multiplier
            multiplier += 1
        return total

    run_int_fn(main, 2 * 1 + 3 * 2 + 4 * 3)
