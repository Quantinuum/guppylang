import guppylang
import pytest
from guppylang.decorator import guppy
from guppylang.std.builtins import array, py
from guppylang.std.quantum import discard_array, measure, qubit

from tests.util import compile_and_get_peak_memory

guppylang.enable_experimental_features()

array_size = 10
n_compilations = 10


@guppy
def main_array() -> None:
    q_array = array(qubit() for _ in range(py(array_size)))
    discard_array(q_array)


@guppy
def main_single_qubit() -> None:
    q = qubit()
    _ = measure(q)


@guppy
def main_list() -> None:
    q_list = [qubit() for _ in range(py(array_size))]
    for q in q_list:
        measure(q)


@pytest.mark.parametrize(
    "guppy_fn",
    [main_array, main_single_qubit, main_list],
    ids=["array", "qubit", "list"],
)
def test_mem_compile_once(benchmark, guppy_fn) -> None:
    benchmark(guppy_fn.compile)
    benchmark.extra_info["memory"] = compile_and_get_peak_memory(guppy_fn)


@pytest.mark.parametrize(
    "guppy_fn",
    [main_array, main_single_qubit, main_list],
    ids=["array", "qubit", "list"],
)
def test_mem_compile_multiple(benchmark, guppy_fn) -> None:
    benchmark(guppy_fn.compile)
    benchmark.extra_info["memory"] = compile_and_get_peak_memory(
        guppy_fn, n_compilations
    )
