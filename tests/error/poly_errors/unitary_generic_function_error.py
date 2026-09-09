from guppylang.decorator import guppy

T = guppy.type_var("T")

@guppy.unitary
class identity:

    @guppy
    def __call__(x: T) -> T:
        return x

@guppy
def main() -> None:
    identity[int](True)


main.compile()
