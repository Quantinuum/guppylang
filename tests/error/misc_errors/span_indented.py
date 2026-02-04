from guppylang.decorator import guppy


def build():
    @guppy
    def foo(x: float) -> int:
        return x

    return foo


build().compile()  # type: ignore
