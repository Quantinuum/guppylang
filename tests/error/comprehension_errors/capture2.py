from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy.declare
def bar(q: qubit @owned) -> bool:
    ...


@guppy
def foo(xs: list[int], q: qubit @owned) -> list[int]:
    return [x for x in xs if bar(q)]


foo.compile()
