from guppylang import guppy

@guppy
def foo(b: bool) -> int:
    if b:
        y = 9
    else:
        return 2


foo.compile()