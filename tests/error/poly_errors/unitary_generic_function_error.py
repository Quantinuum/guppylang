from guppylang.decorator import guppy


@guppy.unitary
class identity:
    T = guppy.type_var("T")

    @guppy
    def __call__(x: T) -> T:
        return x

@guppy
def main() -> None:
    identity[int](True)


main.compile()
