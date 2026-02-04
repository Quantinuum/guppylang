from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned


@guppy.declare
def bar(q: qubit) -> int: ...


@guppy
def foo(n: int, q: qubit @owned) -> list[int]:
    return [bar(q) for _ in range(n)]


foo.compile()
