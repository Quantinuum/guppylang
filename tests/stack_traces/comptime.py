from guppylang import guppy
from guppylang.std.platform import panic


@guppy.comptime
def panicking_func() -> None:
    panic("Always panics")


@guppy.comptime
def main() -> None:
    panicking_func()


main.with_minimal_opt().emulator(n_qubits=1, debug_mode=True).run()
