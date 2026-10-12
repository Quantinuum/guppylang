from guppylang import guppy
from guppylang.std.platform import panic


@guppy
def main() -> None:
    panic("Always panics")


main.with_minimal_opt().emulator(n_qubits=1, debug_mode=True).run()
