from guppylang import guppy

@guppy.enum
class MyEnum:
    Variant1 = {"x": "MyStruct"}

@guppy.struct
class MyStruct:
    field: MyEnum

# This should raise an error during compilation
MyStruct.compile()