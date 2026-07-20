from guppylang import guppy
from guppylang.std.builtins import output



@guppy(daggerable=True)
def test() -> None:
    output("a", True)

test.compile()
