from guppylang import guppy


# Reference to a type that doesn't exist
BadAlias = guppy.type_alias("NonExistentType")


@guppy
def main(x: BadAlias) -> BadAlias:
    return x


main.compile_function()
