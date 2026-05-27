from guppylang import guppy, qubit
from guppylang.std.builtins import PowerControllable


@guppy(control=True)
def control_only(q: qubit) -> None:
    pass


@guppy
def apply_power_control(f: PowerControllable[[qubit], None], q: qubit) -> None:
    f(q)


@guppy
def test(q: qubit) -> None:
    apply_power_control(control_only, q)


test.compile_function()
