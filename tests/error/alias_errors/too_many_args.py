from guppylang import guppy


@guppy.struct
class Box[T]:
    value: T


BoxAlias = guppy.type_alias("BoxAlias", "Box[T]", params=[T])


@guppy
def main(b: BoxAlias[int, bool]) -> int:  # Too many type args: BoxAlias takes 1
    return b.value


main.compile_function()
