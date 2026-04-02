from guppylang import guppy

@guppy.enum
class MyEnum:
    Left = {} 

    @guppy
    def method(self) -> str:
            return "42"

@guppy
def fun() -> None:
    a = MyEnum.method

fun.check()
