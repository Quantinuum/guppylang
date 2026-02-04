from guppylang import guppy

@guppy
def foo() -> None:
    for i in range(
        a
    ): # fmt: skip
        pass


foo.compile()
