from guppylang.decorator import guppy


@guppy
def foo(x: tuple[int, float]) -> None:
    pass


foo.emulator(1)
