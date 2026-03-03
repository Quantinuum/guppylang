from guppylang import guppy, comptime
from guppylang.std.builtins import result


@guppy
def foo(tag: str @ comptime, y: bool) -> None:
    result(tag, y)


@guppy
def main() -> None:
    # each tick or cross is 3 bytes. The cross sends the tag over the limit.
    foo("✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅❌", True)


main.compile()
