from guppylang.decorator import guppy

T = guppy.type_var("T")


@guppy
def foo() -> None:
    def bar(x: T) -> T:
        return x


foo.compile()
