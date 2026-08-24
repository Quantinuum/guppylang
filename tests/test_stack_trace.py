from guppylang import guppy
from guppylang.std.platform import panic

from test_stack_trace_helper import array_out_of_bounds_other_file


@guppy
def always_panic() -> None:
    panic("Always panics")


@guppy
def array_out_of_bounds(x: int) -> int:
    return array_out_of_bounds_other_file(x)


@guppy
def main() -> None:
    array_out_of_bounds(5)


main.emulator(n_qubits=1, debug_mode=True).run()
