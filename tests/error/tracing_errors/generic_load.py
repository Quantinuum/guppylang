from guppylang.decorator import guppy
from guppylang.std.builtins import Function


T = guppy.type_var("T")


@guppy.declare
def generic_func(x: T) -> T: ...


@guppy.comptime
def main() -> Function[[int], int]:
    return generic_func


main.compile()
