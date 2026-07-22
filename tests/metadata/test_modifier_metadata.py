"""Tests that modifier blocks have the correct `unitary` metadata attached."""

from guppylang import guppy
from guppylang.std.angles import angle
from guppylang.std.builtins import control, dagger, power, qubit
from guppylang.std.quantum import discard, rx
from guppylang_internals.tys.ty import UnitaryFlags
from hugr.hugr.base import Hugr
from hugr.ops import FuncDecl, FuncDefn
from tket.metadata import UnitaryFlags as TketUnitaryFlags


def _check_block_metadata(hugr_module: Hugr, unitary_values: list[int]) -> list:
    """Return the metadata dicts of all __WithBlock__ FuncDefn nodes."""

    blocks = []
    for _, data in hugr_module.nodes():
        if isinstance(data.op, FuncDefn) and ".__WithBlock__" in data.op.f_name:
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
        a = angle(1 / 3)
        with dagger:
            rx(t, a)
        discard(t)

    # For test sake we need the original unmodified HUGR
    h = main.with_minimal_opt().compile_function().modules[0]
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

    h = main.with_minimal_opt().compile_function().modules[0]
    _check_block_metadata(h, [UnitaryFlags.Control.value])


# Tests nested modifiers metadata
def test_unitary_metadata_power_dagger_control(use_experimental_features):
    @guppy
    def main() -> None:
        c1 = qubit()
        t = qubit()
        with power(3):
            a = angle(1 / 3)
            with dagger:  # noqa: SIM117
                with control(c1):
                    rx(t, a)
        discard(c1)
        discard(t)

    # For test sake we need the original unmodified HUGR
    h = main.with_minimal_opt().compile_function().modules[0]
    _check_block_metadata(
        h,
        [
            UnitaryFlags.NoFlags.value,
            UnitaryFlags.Dagger.value,
            (UnitaryFlags.Control | UnitaryFlags.Dagger).value,
        ],
    )


def test_unitary_metadata_dagger_power_control(use_experimental_features):
    @guppy
    def main() -> None:
        c1 = qubit()
        t = qubit()
        a = angle(1 / 3)
        with dagger:  # noqa: SIM117
            with power(3):
                with control(c1):
                    rx(t, a)
        discard(c1)
        discard(t)

    # For test sake we need the original unmodified HUGR
    h = main.with_minimal_opt().compile_function().modules[0]
    _check_block_metadata(
        h,
        [
            UnitaryFlags.Dagger.value,
            UnitaryFlags.Dagger.value,
            (UnitaryFlags.Control | UnitaryFlags.Dagger).value,
        ],
    )


def test_unitary_metadata_control_dagger_power(use_experimental_features):
    @guppy
    def main() -> None:
        c1 = qubit()
        t = qubit()
        a = angle(1 / 3)
        with control(c1):  # noqa: SIM117
            with dagger:
                with power(3):
                    rx(t, a)
        discard(c1)
        discard(t)

    # For test sake we need the original unmodified HUGR
    h = main.with_minimal_opt().compile_function().modules[0]
    _check_block_metadata(
        h,
        [
            UnitaryFlags.Control.value,
            (UnitaryFlags.Dagger | UnitaryFlags.Control).value,
            (UnitaryFlags.Dagger | UnitaryFlags.Control).value,
        ],
    )


def test_unitary_metadata_power_control_dagger(use_experimental_features):
    @guppy
    def main() -> None:
        c1 = qubit()
        t = qubit()
        a = angle(1 / 3)
        with power(3):  # noqa: SIM117
            with control(c1):
                with dagger:
                    rx(t, a)
        discard(c1)
        discard(t)

    # For test sake we need the original unmodified HUGR
    h = main.with_minimal_opt().compile_function().modules[0]
    _check_block_metadata(
        h,
        [
            UnitaryFlags.NoFlags.value,
            UnitaryFlags.Control.value,
            (UnitaryFlags.Dagger | UnitaryFlags.Control).value,
        ],
    )


def test_unitary_metadata_dagger_control_power(use_experimental_features):
    @guppy
    def main() -> None:
        c1 = qubit()
        t = qubit()
        a = angle(1 / 3)
        with dagger:  # noqa: SIM117
            with control(c1):
                with power(3):
                    rx(t, a)
        discard(c1)
        discard(t)

    # For test sake we need the original unmodified HUGR
    h = main.with_minimal_opt().compile_function().modules[0]
    _check_block_metadata(
        h,
        [
            UnitaryFlags.Dagger.value,
            (UnitaryFlags.Control | UnitaryFlags.Dagger).value,
            (UnitaryFlags.Control | UnitaryFlags.Dagger).value,
        ],
    )


def test_unitary_metadata_control_power_dagger(use_experimental_features):
    @guppy
    def main() -> None:
        c1 = qubit()
        t = qubit()
        a = angle(1 / 3)
        with control(c1):  # noqa: SIM117
            with power(3):
                with dagger:
                    rx(t, a)
        discard(c1)
        discard(t)

    # For test sake we need the original unmodified HUGR
    h = main.with_minimal_opt().compile_function().modules[0]
    _check_block_metadata(
        h,
        [
            UnitaryFlags.Control.value,
            UnitaryFlags.Control.value,
            (UnitaryFlags.Dagger | UnitaryFlags.Control).value,
        ],
    )


def test_unitary_metadata_function_definition(use_experimental_features):
    @guppy(daggerable=True)
    def dag() -> None:
        pass

    @guppy.comptime(controllable=True)
    def ctrl() -> None:
        pass

    @guppy(controllable=True, daggerable=True)
    def cd() -> None:
        pass

    @guppy.declare(unitary=True)
    def uni() -> None: ...

    @guppy
    def main() -> None:
        dag()
        ctrl()
        cd()
        uni()

    expected_names = {"__main__.dag", "ctrl", "__main__.cd", "__main__.uni"}
    expected_unitary_flags = {
        "__main__.dag": UnitaryFlags.Dagger.value,
        "ctrl": UnitaryFlags.Control.value,
        "__main__.cd": (UnitaryFlags.Control | UnitaryFlags.Dagger).value,
        "__main__.uni": UnitaryFlags.Unitary.value,
    }

    # For test sake we need the original unmodified HUGR
    hugr = main.with_minimal_opt().compile().modules[0]
    for _, data in hugr.nodes():
        if (
            isinstance(data.op, (FuncDefn, FuncDecl))
            and data.op.f_name in expected_names
        ):
            assert data.op.f_name in expected_unitary_flags
            assert (
                data.metadata[TketUnitaryFlags.KEY]
                == expected_unitary_flags[data.op.f_name]
            )
