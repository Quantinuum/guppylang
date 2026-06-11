from guppylang import guppy, qubit
from guppylang.std.builtins import PowerControllable


@guppy(power=True)
def power_only(q: qubit) -> None:
    pass


@guppy
def apply_power_control(f: PowerControllable[[qubit], None], q: qubit) -> None:
    f(q)


@guppy
def test(q: qubit) -> None:
    apply_power_control(power_only, q)


test.compile_function()
