from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.unitary
class foo:

    @guppy
    def __call__(q: int) -> None:
        return 0

@guppy
def main() -> None:
    foo(True)

main.compile()