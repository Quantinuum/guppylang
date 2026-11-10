# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "guppylang==1.2.0",
#     "guppylang-internals==1.2.0",
# ]
# ///

from pathlib import Path
from sys import argv

from guppylang import guppy
from guppylang.std.angles import angle
from guppylang.std.quantum import h, qubit, rx


@guppy.declare
def func1() -> float: ...


@guppy.declare
def func2(f: float, q: qubit) -> float: ...


@guppy
def unknown_rotations(q: qubit) -> None:
    rotation = func1()
    rx(q, angle(rotation))

    # Some operations that we can optimize away.
    h(q)
    h(q)

    other_rotation = func2(rotation + 1.0, q)
    rx(q, angle(other_rotation))


# Output unoptimized Hugr so we can see the effect of optimization during test.
program = unknown_rotations.with_minimal_opt().compile_function()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
