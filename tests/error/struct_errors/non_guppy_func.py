from guppylang.decorator import guppy


@guppy.struct
class MyStruct:
    x: int

    def f(self: "MyStruct") -> None:
        pass


MyStruct.compile()
