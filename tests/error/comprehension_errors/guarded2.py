from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy.declare
def bar(q: qubit) -> bool:
    ...


@guppy
def foo(qs: list[tuple[bool, qubit]] @owned) -> list[int]:
    return [42 for b, q in qs if b if bar(q)]


foo.compile()
