from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy.declare
def bar(q: qubit) -> bool: ...


@guppy
def foo(qs: list[qubit] @owned) -> list[int]:
    return [0 for q in qs if bar(q)]


foo.compile()
