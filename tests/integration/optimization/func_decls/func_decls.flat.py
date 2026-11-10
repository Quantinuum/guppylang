from guppylang import guppy
from guppylang.std.angles import angle
from guppylang.std.quantum import h, qubit, rx


def func_decls_flat():
    @guppy.declare
    def func1() -> float: ...

    @guppy.declare
    def func2(f: float, q: qubit) -> float: ...

    @guppy.comptime
    def unknown_rotations(q: qubit) -> None:
        rotation = func1()
        rx(q, angle(rotation))

        # Some operations that we can optimize away.
        h(q)
        h(q)

        other_rotation = func2(rotation + 1.0, q)
        rx(q, angle(other_rotation))

    return unknown_rotations.with_minimal_opt().compile_function()
