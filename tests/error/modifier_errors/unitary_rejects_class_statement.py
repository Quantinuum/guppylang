from guppylang.decorator import guppy


@guppy
def helper() -> None:
    pass


@guppy.unitary
class Foo:
    dagger = helper

    @guppy
    def __call__() -> None:
        pass
