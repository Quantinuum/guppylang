from guppylang.decorator import guppy


@guppy.unitary
class Foo:
    @guppy
    def __call__() -> None:
        pass

    @guppy
    def other() -> None:
        pass
