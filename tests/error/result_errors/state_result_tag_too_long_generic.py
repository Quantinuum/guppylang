from guppylang import guppy
from guppylang.std.builtins import comptime
from guppylang.std.debug import state_result
from guppylang.std.quantum import discard, qubit

TAG_MAX_LEN = 200

@guppy
def foo(tag: str @ comptime) -> None:
    q1 = qubit()
    state_result(tag, q1)
    discard(q1)


@guppy
def main() -> None:
    foo(comptime("a" * (TAG_MAX_LEN + 1)))


main.compile()
