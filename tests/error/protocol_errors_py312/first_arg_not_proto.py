from guppylang import guppy

@guppy.protocol
class AdderProto[T]:
    @guppy.require
    def add(x: T, y: T) -> T: ...

@guppy.struct
class AdderInt:
    @guppy
    def add(x: int, y: int) -> int:
        return x + y

@guppy
def eat_adder[T: (Copy, Drop), A: AdderProto[T]](a: A, x: T, y: T) -> T:
    return a.add(x, y)

@guppy
def main() -> int:
    return eat_adder(AdderInt, 1, 2)

main.check()
