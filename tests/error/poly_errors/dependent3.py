from guppylang.decorator import guppy
from guppylang.std.lang import Copy, Drop
from guppylang.std.num import nat


@guppy.struct
class Eq[T: (Copy, Drop), x: T, y: T]:
    pass

@guppy
def eq_refl[T: (Copy, Drop), x: T]() -> Eq[T, x, x]:
    return Eq()


@guppy
def main() -> Eq[bool, True, False]:
    return eq_refl()


main.compile()
