from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned


@guppy.declare
def foo(q: array[int, 3]) -> None: ...


@guppy.declare
def use(q: array[int, 3] @owned) -> None: ...


@guppy
def test(q: array[int, 3]) -> None:
    foo(q)
    use(q)


test.compile()
