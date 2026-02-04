from guppylang.decorator import guppy


@guppy
def foo(x: float) -> int:
    return x


# Call check instead of compile
foo.check()
