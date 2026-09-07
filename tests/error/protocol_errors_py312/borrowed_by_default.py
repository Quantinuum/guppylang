from guppylang import guppy
from guppylang.std.lang import owned


@guppy.protocol
class Proto:
    """Empty protocol"""

@guppy
def foo(x: Proto) -> None:
    y = x

@guppy
def main() -> None:
    foo(42)

main.compile()
