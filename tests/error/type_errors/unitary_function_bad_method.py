from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.unitary
class foo:

    @guppy
    def __call__(q: int) -> int:
        return 1 + q

    @guppy
    def daggered(q: int) -> int:
        return 2 + True

@guppy
def main() -> None:
    foo(1)

main.compile()