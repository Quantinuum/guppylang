from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned


@guppy.struct
class MyStruct:
    x: array[int, 1]


@guppy.declare
def use(arr: array[int, 1] @owned) -> None: ...


@guppy
def test(s: MyStruct) -> None:
    p = s.x
    use(s.x)


test.compile()