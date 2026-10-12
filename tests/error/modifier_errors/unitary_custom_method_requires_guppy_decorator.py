from guppylang.decorator import guppy


@guppy.unitary
class Foo:
    @guppy
    def __call__() -> None:
        pass

    def controlled() -> None:
        pass
