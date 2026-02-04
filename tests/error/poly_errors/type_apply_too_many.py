from guppylang.decorator import guppy

T = guppy.type_var("T")


@guppy.declare
def foo(x: T) -> None:
    ...


@guppy
def main() -> None:
    foo[int, float, bool]


main.compile()
