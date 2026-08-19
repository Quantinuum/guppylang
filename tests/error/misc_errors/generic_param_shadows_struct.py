from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy.struct
class MyStruct:
    field: int

    @guppy
    def foo(self: "MyStruct") -> int:
        return self.field


n = guppy.nat_var("MyStruct")


@guppy
def main(x: array[int, n]) -> None:
    # `MyStruct` here refers to the generic nat parameter above (shadowing the
    # struct of the same name), not the struct class, so this must resolve to the
    # ordinary "attribute not found on nat" error rather than being misdiagnosed as
    # an instance method called on the (unrelated, shadowed) struct class.
    MyStruct.foo()


main.compile()
