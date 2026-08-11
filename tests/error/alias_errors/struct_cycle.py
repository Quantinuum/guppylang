from typing import Generic

from guppylang import guppy

T = guppy.type_var("T")


@guppy.struct
class Box(Generic[T]):
    value: T


# Alias whose body refers to itself via a struct type argument
MyAlias = guppy.type_alias("MyAlias", "Box[MyAlias]")


@guppy
def f(x: MyAlias) -> MyAlias:
    return x


f.compile_function()
