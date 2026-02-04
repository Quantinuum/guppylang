from guppylang.decorator import guppy


# `control` is overloaded, so the number of arguments need not be fixed to 1.
# However, the error message says "expected 1 arguments, got 0" when no argument is given.
@guppy
def test() -> None:
    with control():
        pass


test.compile()
