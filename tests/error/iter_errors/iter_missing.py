from guppylang import guppy
from guppylang_internals.decorator import custom_type
from guppylang_internals.tys.ty import NoneType

@custom_type(NoneType())
class MyType:
    """A non-iterable type."""


@guppy
def test(x: MyType) -> None:
    for _ in x:
        pass


test.compile()
