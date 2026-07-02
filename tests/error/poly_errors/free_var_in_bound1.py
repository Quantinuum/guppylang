from guppylang.decorator import guppy

T = guppy.type_var("T", copyable=True, droppable=True)


@guppy
def main[x: T]() -> None:
    ...


main.compile()
