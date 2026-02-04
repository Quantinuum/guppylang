from guppylang import guppy
from guppylang_internals.decorator import custom_type
from guppylang_internals.tys.ty import NoneType

@custom_type(lambda _, ctx: NoneType().to_hugr(ctx))
class MyType:
    """A type where the `__iter__` method has the wrong signature."""

    @guppy.declare
    def __iter__(self: "MyType", x: int) -> "MyType":
        ...


@guppy
def test(x: MyType) -> None:
    for _ in x:
        pass


test.compile()
