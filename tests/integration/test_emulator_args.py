"""End-to-end emulator tests for entrypoint runtime arguments."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from guppylang import guppy
from guppylang.emulator import EmulatorResult
from guppylang.std.builtins import array, output

if TYPE_CHECKING:
    from collections.abc import Callable

    from guppylang.defs import GuppyFunctionDefinition


def _bool_echo() -> GuppyFunctionDefinition[..., None]:
    @guppy
    def main(x: bool) -> None:
        output("x", x)

    return main


def _int_echo() -> GuppyFunctionDefinition[..., None]:
    @guppy
    def main(x: int) -> None:
        output("x", x)

    return main


def _float_echo() -> GuppyFunctionDefinition[..., None]:
    @guppy
    def main(x: float) -> None:
        output("x", x)

    return main


def _bool_array_echo() -> GuppyFunctionDefinition[..., None]:
    @guppy
    def main(xs: array[bool, 3]) -> None:
        output("e0", xs[0])
        output("e1", xs[1])
        output("e2", xs[2])

    return main


def _int_array_echo() -> GuppyFunctionDefinition[..., None]:
    @guppy
    def main(xs: array[int, 3]) -> None:
        output("e0", xs[0])
        output("e1", xs[1])
        output("e2", xs[2])

    return main


def _float_array_echo() -> GuppyFunctionDefinition[..., None]:
    @guppy
    def main(xs: array[float, 3]) -> None:
        output("e0", xs[0])
        output("e1", xs[1])
        output("e2", xs[2])

    return main


@pytest.mark.parametrize(
    ("make_main", "value"),
    [
        pytest.param(_bool_echo, True, id="bool"),
        pytest.param(_int_echo, 7, id="int"),
        pytest.param(_float_echo, 1.5, id="float"),
    ],
)
def test_scalar_arg_roundtrip(
    make_main: Callable[[], GuppyFunctionDefinition[..., None]],
    value: float,
) -> None:
    main = make_main()
    res = main.emulator(n_qubits=1).run(x=value)
    assert res == EmulatorResult([[("x", value)]])


@pytest.mark.parametrize(
    ("make_main", "values"),
    [
        pytest.param(_bool_array_echo, [True, False, True], id="array_bool"),
        pytest.param(_int_array_echo, [1, 2, 3], id="array_int"),
        pytest.param(_float_array_echo, [1.0, 2.0, 3.0], id="array_float"),
    ],
)
def test_array_arg_roundtrip(
    make_main: Callable[[], GuppyFunctionDefinition[..., None]],
    values: list[int] | list[float] | list[bool],
) -> None:
    main = make_main()
    res = main.emulator(n_qubits=1).run(xs=values)
    assert res == EmulatorResult([[(f"e{i}", v) for i, v in enumerate(values)]])


def test_constant_args() -> None:
    @guppy
    def main(theta: float, k: int) -> None:
        output("doubled", theta * 2.0)
        output("k1", k + 1)

    py_theta, py_k = 1.5, 3
    res = main.emulator(n_qubits=1).run(theta=py_theta, k=py_k)
    assert res == EmulatorResult([[("doubled", py_theta * 2.0), ("k1", py_k + 1)]])


def test_constant_args_broadcast_over_shots() -> None:
    @guppy
    def main(theta: float) -> None:
        output("theta", theta)

    py_theta, n_shots = 2.0, 3
    res = main.emulator(n_qubits=1).with_shots(n_shots).run(theta=py_theta)
    assert res == EmulatorResult([[("theta", py_theta)]] * n_shots)


def test_per_shot_args() -> None:
    @guppy
    def main(theta: float, k: int) -> None:
        output("doubled", theta * 2.0)
        output("k1", k + 1)

    shot_inputs = [
        {"theta": 1.0, "k": 10},
        {"theta": 2.5, "k": 20},
        {"theta": 4.0, "k": 30},
    ]
    res = main.emulator(n_qubits=1).run_per_shot(shot_inputs)
    assert res == EmulatorResult(
        [[("doubled", s["theta"] * 2.0), ("k1", s["k"] + 1)] for s in shot_inputs]
    )


@pytest.mark.xfail(
    raises=ValueError,
    reason=(
        "selene's ArgProvider rejects empty lists with 'List for key ... cannot be "
        "empty'. Expected to be fixed in https://github.com/Quantinuum/selene/pull/187."
    ),
    strict=True,
)
def test_empty_array_arg() -> None:
    # TODO: Once https://github.com/Quantinuum/selene/pull/187 is merged and
    # released, remove the xfail mark above.
    @guppy
    def main(xs: array[int, 0]) -> None:
        output("done", 1)

    res = main.emulator(n_qubits=1).run(xs=[])
    assert res == EmulatorResult([[("done", 1)]])
