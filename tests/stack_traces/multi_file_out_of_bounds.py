from guppylang import guppy

from tests.stack_traces.test_helper import array_with_three_elements


@guppy
def array_out_of_bounds(x: int) -> int:
    return array_with_three_elements(x)


@guppy
def main() -> None:
    array_out_of_bounds(5)


main.with_minimal_opt().emulator(n_qubits=1, debug_mode=True).run()
