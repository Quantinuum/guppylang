from guppylang import guppy, comptime
from guppylang.std.array import array
from guppylang.std.num import nat


@guppy.protocol
class Proto:
    @guppy.require
    def foo[n: nat](self, xs: array[int, n]) -> array[int, "comptime(n + 1)"]: ...


@guppy.struct
class MyType:
    @guppy.declare
    def foo[n: nat](self, xs: array[int, n]) -> array[int, "comptime(n + 1)"]: ...


@guppy
def take(x: Proto) -> None:
    x.foo(array(1))


@guppy
def main() -> None:
    take(MyType())


main.compile()
