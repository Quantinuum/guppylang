from typing import Generic

from guppylang import guppy

T = guppy.type_var("T")


@guppy.enum
class Option(Generic[T]):
    Nothing = {}
    Just = {"value": T}


# Alias whose body refers to itself via an enum type argument
MyAlias = guppy.type_alias("MyAlias", "Option[MyAlias]")


@guppy
def f(x: MyAlias) -> MyAlias:
    return x


f.compile_function()
