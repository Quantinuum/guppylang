from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.qsystem import measure
from guppylang.std.quantum import qubit


@guppy(dagger=True)
def test(x: qubit @owned) -> None:
    measure(x)


test.compile_function()
