"""End-to-end emulator tests for entrypoint runtime arguments."""

from __future__ import annotations

import functools

import pytest

from guppylang import guppy
from guppylang.emulator import EmulatorResult
from guppylang.std.builtins import array, result


@functools.cache
def _args_supported() -> bool:
    """Probe whether the toolchain can build & run an entrypoint with arguments.

    TODO: Remove this guard once published releases of tket_exts and the selene
    compiler include the ``tket.argument`` extension.
    """
    try:
        from selene_argreader_plugin import ArgProvider  # noqa: F401
        from tket_exts.tket.argument import ArgumentExtension  # noqa: F401
    except ImportError:
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _args_supported(),
    reason="toolchain does not support the tket.argument extension",
)


def test_constant_args() -> None:
    @guppy
    def main(theta: float, k: int) -> None:
        result("doubled", theta * 2.0)
        result("k1", k + 1)

    py_theta, py_k = 1.5, 3
    res = main.emulator(n_qubits=1).run(theta=py_theta, k=py_k)
    assert res == EmulatorResult([[("doubled", py_theta * 2.0), ("k1", py_k + 1)]])


def test_constant_args_broadcast_over_shots() -> None:
    @guppy
    def main(theta: float) -> None:
        result("theta", theta)

    py_theta, n_shots = 2.0, 3
    res = main.emulator(n_qubits=1).with_shots(n_shots).run(theta=py_theta)
    assert res == EmulatorResult([[("theta", py_theta)]] * n_shots)


def test_per_shot_args() -> None:
    @guppy
    def main(theta: float, k: int) -> None:
        result("doubled", theta * 2.0)
        result("k1", k + 1)

    shot_inputs = [
        {"theta": 1.0, "k": 10},
        {"theta": 2.5, "k": 20},
        {"theta": 4.0, "k": 30},
    ]
    res = main.emulator(n_qubits=1).run_per_shot(shot_inputs)
    assert res == EmulatorResult(
        [[("doubled", s["theta"] * 2.0), ("k1", s["k"] + 1)] for s in shot_inputs]
    )


def test_array_arg() -> None:
    @guppy
    def main(xs: array[float, 3]) -> None:
        result("first", xs[0])
        result("third", xs[2])

    py_xs = [1.0, 2.0, 3.0]
    res = main.emulator(n_qubits=1).run(xs=py_xs)
    assert res == EmulatorResult([[("first", py_xs[0]), ("third", py_xs[2])]])


def test_bool_arg() -> None:
    @guppy
    def main(flag: bool) -> None:
        result("flag", flag)

    py_flag = True
    res = main.emulator(n_qubits=1).run(flag=py_flag)
    assert res == EmulatorResult([[("flag", py_flag)]])
