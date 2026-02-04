from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned


@guppy.declare
def use(q: array[int, 3] @owned) -> None: ...


@guppy
def test(q: array[int, 3] @owned) -> None:
    for i in q:
        i + i
    use(q)

test.compile()
