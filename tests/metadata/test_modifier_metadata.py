"""Tests that modifier blocks have the correct `unitary` metadata attached."""

from guppylang import guppy
from guppylang.std.angles import angle
from guppylang.std.array import array
from guppylang.std.builtins import control, dagger, power, qubit
from guppylang.std.quantum import discard, rx
from guppylang_internals.metadata.common import (
    CONTROLLED_KEY,
    CTRL_DAGGERED_KEY,
    DAGGERED_KEY,
    NUM_CONTROL_QUBITS_KEY,
)
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


def test_custom_modifier_metadata(use_experimental_features):
    @guppy.unitary
    class custom_gate:
        n = guppy.nat_var("n")

        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def daggered(q: qubit) -> None:
            pass

        @guppy
        def controlled(q: qubit, _controls: array[qubit, n]) -> None:
            pass

        @guppy
        def ctrl_daggered(q: qubit, _controls: array[qubit, n]) -> None:
            pass

    @guppy
    def main(
        target: qubit,
        control_one: qubit,
        controls_two: array[qubit, 2],
        controls_three: array[qubit, 3],
    ) -> None:
        with dagger:
            custom_gate(target)
        with control(control_one):
            custom_gate(target)
        with control(controls_two):
            custom_gate(target)
        with control(control_one), dagger:
            custom_gate(target)
        with control(controls_three), dagger:
            custom_gate(target)

    hugr = main.with_minimal_opt().compile_function().modules[0]
    metadata_by_link_name = {
        data.op.f_name: data.metadata
        for _, data in hugr.nodes()
        if isinstance(data.op, FuncDefn)
    }

    custom_keys = {DAGGERED_KEY, CONTROLLED_KEY, CTRL_DAGGERED_KEY}
    [unmodified_metadata] = [
        metadata
        for metadata in metadata_by_link_name.values()
        if all(key in metadata for key in custom_keys)
    ]

    daggered_link = unmodified_metadata[DAGGERED_KEY]
    assert isinstance(daggered_link, str)
    assert NUM_CONTROL_QUBITS_KEY not in metadata_by_link_name[daggered_link]

    controlled_links = unmodified_metadata[CONTROLLED_KEY]
    assert isinstance(controlled_links, list)
    assert all(isinstance(link, str) for link in controlled_links)
    assert [
        metadata_by_link_name[link][NUM_CONTROL_QUBITS_KEY] for link in controlled_links
    ] == [1, 2]

    ctrl_daggered_links = unmodified_metadata[CTRL_DAGGERED_KEY]
    assert isinstance(ctrl_daggered_links, list)
    assert all(isinstance(link, str) for link in ctrl_daggered_links)
    assert [
        metadata_by_link_name[link][NUM_CONTROL_QUBITS_KEY]
        for link in ctrl_daggered_links
    ] == [1, 3]
