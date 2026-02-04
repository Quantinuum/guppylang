from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy.declare
def bar(q: qubit @owned) -> int: ...


@guppy.declare
def baz(q: qubit) -> int: ...


@guppy
def foo(qs: list[qubit] @owned) -> list[int]:
    return [baz(q) for q in qs if bar(q)]


foo.compile()
