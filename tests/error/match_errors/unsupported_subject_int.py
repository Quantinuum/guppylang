from tests.util import compile_guppy
from guppylang.std.quantum import qubit


@compile_guppy
def main() -> None:
    match qubit():
        case _:
            pass
