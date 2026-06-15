from guppylang.decorator import guppy
from guppylang.std.builtins import Fn

@guppy.struct(frozen=True)
class MyStruct:
    @guppy
    def will_be_partial(self, a: int) -> None:
        pass

@guppy
def takes_int(func: Fn[[int], None]) -> None:
    pass

@guppy
def main() -> None:
    t = MyStruct()
    takes_int(t.will_be_partial)

main.compile()
