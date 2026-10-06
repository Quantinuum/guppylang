from guppylang import guppy
from guppylang.std.num import int


@guppy
def main() -> int:
    # This should internally use the `UnwrapOpCompiler` which relies on a panic built
    # through a global compiler function, therefore testing stack traces for panics
    # that are not directly annotated.
    return int(0.0 / 0.0)


main.with_minimal_opt().emulator(n_qubits=1, debug_mode=True).run()
