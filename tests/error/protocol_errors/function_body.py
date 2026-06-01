from guppylang.decorator import guppy


@guppy.protocol
class MyProto:
    @guppy.require
    def foo(self: "MyProto", x: int) -> str:
        return "abcdef"

@guppy
def bar(f: MyProto, x: int) -> str:
    return f.foo(x)

@guppy.struct
class MyStruct:
    @guppy
    def foo(self, x: int) -> str:
        return ""

@guppy
def main() -> str:
    f = MyStruct()
    return bar(f, 42)

main.compile()
