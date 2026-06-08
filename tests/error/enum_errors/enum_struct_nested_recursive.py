from guppylang import guppy


@guppy.enum
class MyEnum:
    Variant1 = {"x": "tuple[MyStruct, int]"}


@guppy.struct
class MyStruct:
    field: "list[MyEnum]"


MyEnum.compile()
