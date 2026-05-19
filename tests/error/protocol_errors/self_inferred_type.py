from guppylang import guppy

@guppy.protocol
class MyProto:
    @guppy.require
    def foo(self) -> None: ...

@guppy
def bar(f: MyProto) -> None:
    return baz(f)

@guppy
def baz(f: MyProto) -> None:
    return f.foo()

@guppy.struct
class MyStruct:
    @guppy
    def foo(self) -> None:
        return

@guppy
def main() -> None:
    bar(MyStruct())

MyProto.check()
main.check()
