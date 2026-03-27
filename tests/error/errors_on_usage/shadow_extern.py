from guppylang import guppy

x = guppy._extern("x", ty="int")


@guppy
def main(b: bool) -> int:
    if b:
        x = 4
    return x


main.compile_function()
