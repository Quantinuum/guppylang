from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import measure, qubit


@guppy(daggerable=True)
def test(x: qubit @owned) -> None:
    measure(x)


test.compile_function()
