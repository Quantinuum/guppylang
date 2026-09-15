from guppylang.decorator import guppy


@guppy.unitary
class Foo:
    @guppy
    def __call__() -> None:
        pass

    @guppy(controllable=True)
    def daggered() -> None:
        pass
