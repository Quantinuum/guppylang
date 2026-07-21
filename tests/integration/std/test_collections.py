from typing import Self

from guppylang import guppy
from guppylang.std.collections import (
    BTreeMap,
    Stack,
    empty_btree_map,
    empty_stack,
    PriorityQueue,
    empty_priority_queue,
    Queue,
    empty_queue,
)
import pytest
from guppylang.emulator import EmulatorError
from guppylang.std.quantum import qubit, x as x_gate
from guppylang_internals.error import GuppyError


# `_Ord` is intentionally private. These structs exercise its current structural
# compatibility only; exposing a public ordering protocol remains a TODO.
@guppy.struct(frozen=True)
class _CustomOrdKey:
    value: int

    @guppy
    def __lt__(self, other: Self) -> bool:
        return self.value < other.value

    @guppy
    def __eq__(self, other: Self) -> bool:
        return self.value == other.value


@guppy.struct(frozen=True)
class _NonReflexiveKey:
    value: int

    @guppy
    def __lt__(self, other: Self) -> bool:
        return self.value < other.value

    @guppy
    def __eq__(self, other: Self) -> bool:
        return self.value < other.value


def test_btree_map_empty(run_int_fn) -> None:
    @guppy
    def main() -> int:
        btree_map: BTreeMap[int, int, 3] = empty_btree_map()
        size = len(btree_map)
        btree_map.discard_empty()
        return size

    run_int_fn(main, 0)


def test_btree_map_insert_and_lookup(run_int_fn) -> None:
    @guppy
    def main() -> int:
        btree_map: BTreeMap[int, int, 10] = empty_btree_map()
        for i in range(10):
            btree_map.insert(i, i * 2).unwrap_nothing()
        btree_map.get(10).unwrap_nothing()
        return btree_map.get(7).unwrap() + 100 * len(btree_map)

    run_int_fn(main, 1014)


def test_btree_map_get_rejects_linear_values() -> None:
    @guppy
    def main() -> None:
        btree_map: BTreeMap[int, qubit, 1] = empty_btree_map()
        btree_map.insert(0, qubit()).unwrap_nothing()
        btree_map.get(0).unwrap().measure()

    with pytest.raises(GuppyError, match="copyable type"):
        main.check()


def test_btree_map_replaces_at_capacity(run_int_fn) -> None:
    @guppy
    def main() -> int:
        btree_map: BTreeMap[int, int, 4] = empty_btree_map()
        for i in range(4):
            btree_map.insert(i, i).unwrap_nothing()
        displaced = btree_map.insert(2, 10).unwrap()
        return 100 * len(btree_map) + 10 * displaced + btree_map.get(2).unwrap()

    run_int_fn(main, 430)


def test_btree_map_float_keys_and_signed_zero(run_int_fn) -> None:
    @guppy
    def main() -> int:
        btree_map: BTreeMap[float, int, 3] = empty_btree_map()
        btree_map.insert(-0.0, 1).unwrap_nothing()
        displaced = btree_map.insert(0.0, 2).unwrap()
        btree_map.insert(1.0 / 0.0, 3).unwrap_nothing()
        return 100 * len(btree_map) + 10 * displaced + btree_map.get(-0.0).unwrap()

    run_int_fn(main, 212)


def test_btree_map_rejects_nan_key(run_int_fn) -> None:
    @guppy
    def main() -> int:
        btree_map: BTreeMap[float, int, 1] = empty_btree_map()
        btree_map.insert(0.0 / 0.0, 1).unwrap_nothing()
        return 0

    with pytest.raises(EmulatorError, match="key must be reflexive"):
        run_int_fn(main, 0)


def test_btree_map_remove_and_reinsert(run_int_fn) -> None:
    @guppy
    def main() -> int:
        btree_map: BTreeMap[int, int, 10] = empty_btree_map()
        for i in range(10):
            btree_map.insert(i, i).unwrap_nothing()
        removed = btree_map.remove(5).unwrap()
        btree_map.remove(10).unwrap_nothing()
        for i in range(5):
            btree_map.remove(i).unwrap()
        btree_map.insert(10, 20).unwrap_nothing()
        return 100 * len(btree_map) + 10 * removed + btree_map.get(10).unwrap()

    run_int_fn(main, 570)


def test_btree_map_remove_all_and_discard_empty(run_int_fn) -> None:
    @guppy
    def main() -> int:
        btree_map: BTreeMap[int, int, 10] = empty_btree_map()
        for i in range(10):
            btree_map.insert(i, i).unwrap_nothing()
        for i in range(10):
            btree_map.remove(i).unwrap()
        size = len(btree_map)
        btree_map.discard_empty()
        return size

    run_int_fn(main, 0)


def test_btree_map_deletion_rebalances_and_collapses_root(run_int_fn) -> None:
    @guppy
    def main() -> int:
        btree_map: BTreeMap[int, int, 20] = empty_btree_map()
        for i in range(20):
            btree_map.insert(i, i).unwrap_nothing()

        total = 0
        # Deleting from both outer ranges makes top-down deletion borrow from both
        # sides where possible, then merge minimum-sized siblings as they empty.
        for i in range(7):
            total += btree_map.remove(i).unwrap()
        for i in range(7):
            total += btree_map.remove(19 - i).unwrap()
        for i in range(7, 13):
            total += btree_map.remove(i).unwrap()

        btree_map.discard_empty()
        return total

    run_int_fn(main, sum(range(20)))


def test_btree_map_reuses_nodes_after_deletion(run_int_fn) -> None:
    @guppy
    def main() -> int:
        btree_map: BTreeMap[int, int, 10] = empty_btree_map()
        for i in range(10):
            btree_map.insert(i, i).unwrap_nothing()
        for i in range(10):
            btree_map.remove(i).unwrap()

        # A second full tree must be able to allocate every slot released by the
        # first tree, including nodes released by merges and root collapse.
        for i in range(10):
            btree_map.insert(10 + i, 10 + i).unwrap_nothing()
        total = 0
        for i in range(10):
            total += btree_map.remove(10 + i).unwrap()
        btree_map.discard_empty()
        return total

    run_int_fn(main, sum(range(10, 20)))


def test_btree_map_iterates_in_ascending_key_order(run_int_fn) -> None:
    @guppy
    def main() -> int:
        btree_map: BTreeMap[int, int, 10] = empty_btree_map()
        for i in range(10):
            btree_map.insert(9 - i, i).unwrap_nothing()
        result = 0
        multiplier = 1
        for key, value in btree_map:
            result += multiplier * (10 * key + value)
            multiplier += 1
        return result

    run_int_fn(main, sum((i + 1) * (10 * i + 9 - i) for i in range(10)))


def test_btree_map_iteration_consumes_linear_values(run_int_fn) -> None:
    @guppy
    def main() -> int:
        btree_map: BTreeMap[int, qubit, 10] = empty_btree_map()
        for i in range(10):
            value = qubit()
            if i == 4:
                x_gate(value)
            btree_map.insert(9 - i, value).unwrap_nothing()

        result = 0
        position = 1
        for _key, value in btree_map:
            if value.measure():
                result += position
            position += 1
        return result

    # The marked linear value has key 5, so ordered draining measures it sixth.
    run_int_fn(main, 6, num_qubits=10)


def test_btree_map_supports_private_structural_ordering(run_int_fn) -> None:
    @guppy
    def main() -> int:
        btree_map: BTreeMap[_CustomOrdKey, int, 3] = empty_btree_map()
        btree_map.insert(_CustomOrdKey(2), 20).unwrap_nothing()
        btree_map.insert(_CustomOrdKey(1), 10).unwrap_nothing()
        return btree_map.get(_CustomOrdKey(1)).unwrap()

    run_int_fn(main, 10)


def test_btree_map_rejects_non_reflexive_private_key(run_int_fn) -> None:
    @guppy
    def main() -> int:
        btree_map: BTreeMap[_NonReflexiveKey, int, 1] = empty_btree_map()
        btree_map.insert(_NonReflexiveKey(1), 1).unwrap_nothing()
        return 0

    with pytest.raises(EmulatorError, match="key must be reflexive"):
        run_int_fn(main, 0)


def test_stack(run_int_fn) -> None:
    @guppy
    def main() -> int:
        stack: Stack[int, 10] = empty_stack()
        for i in range(10):
            stack.push(i)
        s = 0
        i = 1
        while len(stack) > 0:
            x = stack.pop()
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
            stack.push(i)
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
            pq.push(i, 9 - i)
        s = 0
        multiplier = 1
        while len(pq) > 0:
            _priority, value = pq.pop()
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
            pq.push(i, 9 - i)
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
            pq.push(i, i)
        # Pop twice, then push a couple more values after freeing space.
        _, _ = pq.pop()
        _, _ = pq.pop()
        for i in range(5, 7):
            pq.push(i, i)
        # Pop twice again and then push more values to exercise repeated cycles.
        _, _ = pq.pop()
        _, _ = pq.pop()
        for i in range(7, 9):
            pq.push(i, i)
        # Drain remaining values in priority order and verify they are still ordered.
        total = 0
        multiplier = 1
        while len(pq) > 0:
            _, value = pq.pop()
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
            queue.push(i)
        s = 0
        i = 1
        while len(queue) > 0:
            x = queue.pop()
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
            queue.push(i)
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
            queue.push(i)
        return len(queue)

    run_int_fn(main, 5)


def test_queue_beyond_full() -> None:
    """Tests that pushing beyond the queue's maximum capacity raises a panic."""

    @guppy
    def main() -> None:
        queue: Queue[int, 1] = empty_queue()
        for i in range(2):
            queue.push(i)

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
            queue.push(i)

        for _ in range(2):
            queue.pop()

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
            q.push(i)

        for _ in range(2):
            q.pop()

        for i in range(4, 6):
            q.push(i)
        q.pop()
        q.push(6)
        q.pop()
        q.push(7)
        q.pop()
        q.push(8)
        q.pop()
        q.push(9)
        total = 0
        multiplier = 1

        while len(q) > 0:
            x = q.pop()
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
            q.push(i)
        for _ in range(2):
            q.pop()
        for i in range(3, 5):
            q.push(i)
        return len(q)

    run_int_fn(main, 3)


def test_queue_wraparound_iter(run_int_fn) -> None:
    """Tests that the queue maintains insertion order even when
    usage causes internal slots to be reused."""

    @guppy
    def main() -> int:
        q: Queue[int, 5] = empty_queue()
        for i in range(3):
            q.push(i)
        for _ in range(2):
            q.pop()
        for i in range(3, 5):
            q.push(i)
        total = 0
        multiplier = 1
        for x in q:
            total += x * multiplier
            multiplier += 1
        return total

    run_int_fn(main, 2 * 1 + 3 * 2 + 4 * 3)
