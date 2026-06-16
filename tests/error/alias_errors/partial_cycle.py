from guppylang import guppy

# Alias1 is outside the cycle, but leads into it (Alias2 <-> Alias3)
Alias1 = guppy.type_alias("Alias2")
Alias2 = guppy.type_alias("Alias3")
Alias3 = guppy.type_alias("Alias2")


@guppy
def main(x: Alias1) -> Alias1:
    return x


main.compile_function()
