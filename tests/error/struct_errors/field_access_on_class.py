from guppylang.decorator import guppy


@guppy.struct
class MyStruct:
    field: int

    @guppy
    def foo(self: "MyStruct") -> int:
        return self.field


@guppy
def main() -> int:
    # `field` is a data field, not an instance method, so this must fall through to
    # the ordinary "attribute not found" error rather than being misdiagnosed as an
    # instance method called on the class.
    return MyStruct.field


main.compile()
