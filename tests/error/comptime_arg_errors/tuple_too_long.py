from guppylang import comptime, guppy


@guppy
def foo(t: tuple[int] @ comptime) -> int:
    return t[0]


@guppy
def main() -> int:
    return foo(comptime((1, 2)))


main.compile()
