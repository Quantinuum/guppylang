from guppylang.decorator import guppy


@guppy.struct
class MyStruct:
    field: int

    @guppy
    def foo(self: "MyStruct") -> int:
        return self.field


@guppy
def main() -> int:
    # `field` is a data field, not a method, so this must raise the field-specific
    # "instance field accessed on class" error, not the method-specific one.
    return MyStruct.field


main.compile()
