from guppylang.decorator import guppy


@guppy.struct
class MyStruct:
    field: int

    @guppy
    def foo(self: "MyStruct") -> int:
        return self.field


# A global *value* of function type that happens to return a `MyStruct`, but is
# not `MyStruct`'s own constructor. Regression test: this must not be confused
# with a bare reference to the `MyStruct` class itself, even though both are
# global names typed `int -> MyStruct`.
mk_struct = guppy._extern("mk_struct", ty="Function[[int], MyStruct]")


@guppy
def main() -> None:
    # Must be the plain "attribute not found" error, not "instance method
    # accessed on class" - `mk_struct` genuinely has no `foo` attribute.
    mk_struct.foo


main.check()
