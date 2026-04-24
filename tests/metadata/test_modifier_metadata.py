"""Tests that modifier blocks have the correct `unitary` metadata attached."""

import guppylang as _guppylang
from guppylang import guppy
from guppylang.std.angles import angle
from guppylang.std.builtins import control, dagger, power, qubit
from guppylang.std.quantum import discard, rx
from guppylang_internals.tys.ty import UnitaryFlags
from hugr.hugr.base import Hugr
from hugr.ops import FuncDefn

_guppylang.enable_experimental_features()


def _check_block_metadata(
    hugr_module: Hugr, unitary_values: list[int] | None = None
) -> list:
    """Return the metadata dicts of all __WithBlock__ FuncDefn nodes."""

    blocks = []
    for _, data in hugr_module.nodes():
        if isinstance(data.op, FuncDefn) and data.op.f_name.startswith("__WithBlock__"):
            blocks.append(data.metadata)

    if unitary_values is not None:
        assert len(blocks) == len(unitary_values)
        for block, unitary_value in zip(blocks, unitary_values, strict=True):
            assert block["unitary"] == unitary_value

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


def test_unitary_metadata_power_only():
    @guppy
    def main() -> None:
        t = qubit()
        with power(3):
            rx(t, angle(1 / 3))
        discard(t)

    h = main.compile_function().modules[0]
    _check_block_metadata(h, [UnitaryFlags.Power.value])


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
            UnitaryFlags.Power.value,
            (UnitaryFlags.Dagger | UnitaryFlags.Power).value,
            (UnitaryFlags.Control | UnitaryFlags.Dagger | UnitaryFlags.Power).value,
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
            (UnitaryFlags.Power | UnitaryFlags.Dagger).value,
            (UnitaryFlags.Control | UnitaryFlags.Power | UnitaryFlags.Dagger).value,
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
            (UnitaryFlags.Power | UnitaryFlags.Dagger | UnitaryFlags.Control).value,
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
            UnitaryFlags.Power.value,
            (UnitaryFlags.Control | UnitaryFlags.Power).value,
            (UnitaryFlags.Dagger | UnitaryFlags.Control | UnitaryFlags.Power).value,
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
            (UnitaryFlags.Power | UnitaryFlags.Control | UnitaryFlags.Dagger).value,
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
            (UnitaryFlags.Power | UnitaryFlags.Control).value,
            (UnitaryFlags.Dagger | UnitaryFlags.Power | UnitaryFlags.Control).value,
        ],
    )
