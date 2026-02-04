from guppylang import guppy
from guppylang_internals.decorator import custom_type
from guppylang_internals.tys.ty import NoneType

@custom_type(lambda _, ctx: NoneType().to_hugr(ctx))
class MyIter:
    """An iterator that is missing the `__next__` method."""

    @guppy.declare
    def __hasnext__(self: "MyIter") -> tuple[bool, "MyIter"]:
        ...

    @guppy.declare
    def __end__(self: "MyIter") -> None:
        ...


@custom_type(lambda _, ctx: NoneType().to_hugr(ctx))
class MyType:
    """Type that produces the iterator above."""

    @guppy.declare
    def __iter__(self: "MyType") -> MyIter:
        ...


@guppy
def test(x: MyType) -> None:
    for _ in x:
        pass


test.compile()
