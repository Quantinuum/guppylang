from guppylang.std.builtins import result
from tests.util import compile_guppy

@compile_guppy
def foo(y: bool) -> None:
    # each tick or cross is 3 bytes. The cross sends the tag over the limit.
    result("✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅❌", y)
