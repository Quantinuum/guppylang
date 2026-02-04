from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy.declare
def bar(q: qubit) -> list[qubit]: ...


@guppy
def foo(qs: list[qubit] @owned) -> list[qubit]:
    return [r for q in qs for r in bar(q)]


foo.compile()
