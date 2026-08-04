from guppylang import guppy

@guppy.struct
class OverloadErrStruct:
    @guppy
    def func1(self, x: int) -> int:
        return x + 1

    @guppy
    @staticmethod
    def func2(x: str) -> int:
        return 3

    @guppy.overload(func1, func2)
    def overloaded() -> None: ...

@guppy
def main() -> None:
    o = OverloadErrStruct()
    o.overloaded("a")

main.compile()