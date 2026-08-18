from guppylang.decorator import guppy


@guppy.unitary
class foo:

    @guppy
    def __call__(q: int) -> int:
        return 1


@guppy
def main() -> None:
    foo(1)

main.compile()