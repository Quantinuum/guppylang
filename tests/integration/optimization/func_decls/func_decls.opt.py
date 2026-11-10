from guppylang import guppy
from guppylang.std.angles import angle
from guppylang.std.quantum import qubit, rx


def func_decls_opt():
    @guppy.declare
    def func1() -> float: ...

    @guppy.declare
    def func2(f: float, q: qubit) -> float: ...

    @guppy
    def unknown_rotations(q: qubit) -> None:
        rotation = func1()
        rx(q, angle(rotation))

        other_rotation = func2(rotation + 1.0, q)
        rx(q, angle(other_rotation))

    return unknown_rotations.compile_function()
