from guppylang import guppy


MyAlias = guppy.type_alias("MyAlias")


@guppy
def main(x: MyAlias) -> MyAlias:
    return x


main.compile_function()
