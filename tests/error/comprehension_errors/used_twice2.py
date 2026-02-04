from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy.declare
def bar(q: qubit @owned) -> bool:
    ...


@guppy
def foo(qs: list[qubit] @owned) -> list[qubit]:
    return [q for q in qs if bar(q)]


foo.compile()
