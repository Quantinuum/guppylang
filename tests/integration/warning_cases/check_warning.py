from guppylang import rich_warnings
from guppylang.decorator import guppy


@guppy
def foo() -> int:
    if False:
        return 1
    return 0


with rich_warnings():
    foo.check()
