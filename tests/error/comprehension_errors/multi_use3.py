from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy.declare
def bar(q: qubit @owned) -> bool:
    ...


@guppy
def foo(qs: list[qubit] @owned, xs: list[int]) -> list[int]:
    return [x for q in qs for x in xs if bar(q)]


foo.compile()
