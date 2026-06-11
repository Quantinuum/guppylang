"""Tests that modifier blocks have the correct `unitary` metadata attached."""

import guppylang as _guppylang
from guppylang import guppy
from guppylang.std.angles import angle
from guppylang.std.builtins import control, dagger, power, qubit
from guppylang.std.quantum import discard, rx
from guppylang_internals.tys.ty import UnitaryFlags
from hugr.hugr.base import Hugr
from hugr.ops import FuncDefn
from tket.metadata import UnitaryFlags as TketUnitaryFlags

_guppylang.enable_experimental_features()


def _check_block_metadata(hugr_module: Hugr, unitary_values: list[int]) -> list:
    """Return the metadata dicts of all __WithBlock__ FuncDefn nodes."""

    blocks = []
    for _, data in hugr_module.nodes():
        if isinstance(data.op, FuncDefn) and data.op.f_name.startswith("__WithBlock__"):
            blocks.append(data.metadata)

    assert len(blocks) == len(unitary_values)
    for block, unitary_value in zip(blocks, unitary_values, strict=True):
        assert block[TketUnitaryFlags.KEY] == unitary_value

    return blocks


# Test single modifiers metadata
def test_unitary_metadata_dagger_only():
    @guppy
    def main() -> None:
        t = qubit()
        with dagger:
            rx(t, angle(1 / 3))
        discard(t)

    h = main.compile_function().modules[0]
    _check_block_metadata(h, [UnitaryFlags.Dagger.value])


def test_unitary_metadata_control_only():
    @guppy
    def main() -> None:
        c1 = qubit()
        t = qubit()
        with control(c1):
            rx(t, angle(1 / 3))
        discard(c1)
        discard(t)

    h = main.compile_function().modules[0]
    _check_block_metadata(h, [UnitaryFlags.Control.value])


# Tests nested modifiers metadata
def test_unitary_metadata_power_dagger_control():
    @guppy
    def main() -> None:
        c1 = qubit()
        t = qubit()
        with power(3):  # noqa: SIM117
            with dagger:
                with control(c1):
                    rx(t, angle(1 / 3))
        discard(c1)
        discard(t)

    h = main.compile_function().modules[0]
    _check_block_metadata(
        h,
        [
            UnitaryFlags.NoFlags.value,
            UnitaryFlags.Dagger.value,
            (UnitaryFlags.Control | UnitaryFlags.Dagger).value,
        ],
    )


def test_unitary_metadata_dagger_power_control():
    @guppy
    def main() -> None:
        c1 = qubit()
        t = qubit()
        with dagger:  # noqa: SIM117
            with power(3):
                with control(c1):
                    rx(t, angle(1 / 3))
        discard(c1)
        discard(t)

    h = main.compile_function().modules[0]
    _check_block_metadata(
        h,
        [
            UnitaryFlags.Dagger.value,
            UnitaryFlags.Dagger.value,
            (UnitaryFlags.Control | UnitaryFlags.Dagger).value,
        ],
    )


def test_unitary_metadata_control_dagger_power():
    @guppy
    def main() -> None:
        c1 = qubit()
        t = qubit()
        with control(c1):  # noqa: SIM117
            with dagger:
                with power(3):
                    rx(t, angle(1 / 3))
        discard(c1)
        discard(t)

    h = main.compile_function().modules[0]
    _check_block_metadata(
        h,
        [
            UnitaryFlags.Control.value,
            (UnitaryFlags.Dagger | UnitaryFlags.Control).value,
            (UnitaryFlags.Dagger | UnitaryFlags.Control).value,
        ],
    )


def test_unitary_metadata_power_control_dagger():
    @guppy
    def main() -> None:
        c1 = qubit()
        t = qubit()
        with power(3):  # noqa: SIM117
            with control(c1):
                with dagger:
                    rx(t, angle(1 / 3))
        discard(c1)
        discard(t)

    h = main.compile_function().modules[0]
    _check_block_metadata(
        h,
        [
            UnitaryFlags.NoFlags.value,
            UnitaryFlags.Control.value,
            (UnitaryFlags.Dagger | UnitaryFlags.Control).value,
        ],
    )


def test_unitary_metadata_dagger_control_power():
    @guppy
    def main() -> None:
        c1 = qubit()
        t = qubit()
        with dagger:  # noqa: SIM117
            with control(c1):
                with power(3):
                    rx(t, angle(1 / 3))
        discard(c1)
        discard(t)

    h = main.compile_function().modules[0]
    _check_block_metadata(
        h,
        [
            UnitaryFlags.Dagger.value,
            (UnitaryFlags.Control | UnitaryFlags.Dagger).value,
            (UnitaryFlags.Control | UnitaryFlags.Dagger).value,
        ],
    )


def test_unitary_metadata_control_power_dagger():
    @guppy
    def main() -> None:
        c1 = qubit()
        t = qubit()
        with control(c1):  # noqa: SIM117
            with power(3):
                with dagger:
                    rx(t, angle(1 / 3))
        discard(c1)
        discard(t)

    h = main.compile_function().modules[0]
    _check_block_metadata(
        h,
        [
            UnitaryFlags.Control.value,
            UnitaryFlags.Control.value,
            (UnitaryFlags.Dagger | UnitaryFlags.Control).value,
        ],
    )
