from guppylang.decorator import guppy
from typing import Callable

@guppy.struct
class MyStruct:
    @guppy
    def will_be_partial(self, a: int) -> None:
        pass

@guppy
def takes_int(func: Callable[[int], None]) -> None:
    pass

@guppy
def main() -> None:
    t = MyStruct()
    takes_int(t.will_be_partial)

main.compile()
