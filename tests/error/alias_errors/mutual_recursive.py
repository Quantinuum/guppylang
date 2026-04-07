from guppylang import guppy


Alias1 = guppy.type_alias("Alias2")
Alias2 = guppy.type_alias("Alias1")


@guppy
def main(x: Alias1) -> Alias2:
    return x


main.compile_function()
