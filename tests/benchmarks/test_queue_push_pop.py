from guppylang.decorator import guppy
from guppylang.std.collections import Queue, empty_queue


@guppy
def queue_push_benchmark() -> int:
    q: Queue[int, 10000] = empty_queue()
    for i in range(10000):
        q = q.push(i)
    # Return the length so the value is used and not optimized away.
    return len(q)


@guppy
def queue_push_pop_benchmark() -> int:
    q: Queue[int, 10000] = empty_queue()
    for i in range(10000):
        q = q.push(i)
    total = 0
    while len(q) > 0:
        x, q = q.pop()
        total += x
    return total


def test_queue_push_benchmark(benchmark):
    def run():
        # Run the benchmark function (no args) in the emulator with a simple simulator
        return queue_push_benchmark.emulator(0).coinflip_sim().with_seed(42).run()

    benchmark(run)


def test_queue_push_pop_benchmark(benchmark):
    def run():
        # Run the benchmark function (no args) in the emulator with a simple simulator
        return queue_push_pop_benchmark.emulator(0).coinflip_sim().with_seed(42).run()

    benchmark(run)
