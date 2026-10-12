from guppylang.decorator import guppy
from guppylang.std.quantum import qubit

@guppy
def foo() -> None:
    pass

@guppy.comptime
def main(q: qubit) -> qubit:
    foo.compile()
    return q

main.compile()
