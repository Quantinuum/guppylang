from typing import TYPE_CHECKING

from guppylang.decorator import guppy

if TYPE_CHECKING:
    from guppylang.std.builtins import Function


@guppy.struct
class MyStruct:
    field: int

    @guppy
    def foo(self: "MyStruct") -> int:
        return self.field


@guppy
def main(mk_struct: "Function[[int], MyStruct]") -> None:
    # `mk_struct` is a local parameter, not a global name, so it must not be
    # confused with a bare reference to the `MyStruct` class - plain "attribute
    # not found" error expected, not "instance method accessed on class".
    mk_struct.foo


main.compile()
