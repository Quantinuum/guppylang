from guppylang.decorator import guppy


@guppy.struct
class MyStruct:
    x: int
    y: bool


@guppy
def foo() -> MyStruct:
    return MyStruct(42, False)


@guppy
def bar() -> None:
    foo().x += 1


bar.compile()
