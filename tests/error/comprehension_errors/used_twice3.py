from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy.declare
def bar(q: qubit @owned) -> list[int]:
    ...


@guppy
def foo(qs: list[qubit] @owned) -> list[qubit]:
    return [q for q in qs for x in bar(q)]


foo.compile()
