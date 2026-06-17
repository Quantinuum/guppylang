from typing import no_type_check

import numpy as np
import pytest
from guppylang import guppy
from guppylang.defs import GuppyFunctionDefinition
from guppylang.std.angles import angle
from guppylang.std.builtins import array, comptime
from guppylang.std.qsystem import random, rz, utils
from guppylang.std.quantum import cx, discard_array, qubit, x, y, z
from pytket import Circuit, OpType


def random_layered_circuit(n_qubits: int, depth: int, seed: int) -> Circuit:
    rng = np.random.default_rng(seed=seed)
    circuit = Circuit(n_qubits=n_qubits)

    for _ in range(depth):
        for q in range(circuit.n_qubits):
            circuit.Rz(rng.uniform(0, 4), q)
        qubits = rng.permutation(circuit.n_qubits)
        for i in range(0, circuit.n_qubits - 1, 2):
            circuit.CX(qubits[i], qubits[i + 1])

    return circuit


n = guppy.nat_var("n")


@guppy
@no_type_check
def apply_pauli_frame(qs: array[qubit, n], frame_ints: array[int, n]) -> None:
    for idx in range(n):
        if frame_ints[idx] == 1:
            x(qs[idx])
        elif frame_ints[idx] == 2:
            y(qs[idx])
        elif frame_ints[idx] == 3:
            z(qs[idx])


def build_guppy_circuit_comptime(circ: Circuit, seed: int) -> GuppyFunctionDefinition:
    gate_map: dict[OpType, GuppyFunctionDefinition] = {OpType.Rz: rz}

    @guppy.comptime
    @no_type_check
    def comptime_circuit() -> None:
        rng = random.RNG(seed + utils.get_current_shot())
        frame_ints = array(
            rng.random_int_bounded(4) for _ in range(comptime(circ.n_qubits))
        )
        rng.discard()

        q = array(qubit() for _ in range(comptime(circ.n_qubits)))
        apply_pauli_frame(q, frame_ints)

        for com in circ.get_commands():
            if (op_type := com.op.type) in gate_map:
                gate_map[op_type](
                    q[com.qubits[0].index[0]],
                    *[angle(float(ang)) for ang in com.op.params],
                )
            elif op_type == OpType.CX:
                cx(q[com.qubits[0].index[0]], q[com.qubits[1].index[0]])

        apply_pauli_frame(q, frame_ints)
        discard_array(q)

    return comptime_circuit


@pytest.fixture
def circuit_seed():
    seed = int(np.random.SeedSequence().generate_state(1)[0])
    circ = random_layered_circuit(n_qubits=32, depth=24, seed=seed)

    return circ, seed


def test_circuit_comptime_check(benchmark, circuit_seed):
    def circuit_comptime_check():
        build_guppy_circuit_comptime(*circuit_seed).check()

    benchmark.pedantic(circuit_comptime_check, rounds=25)


def test_circuit_comptime_compile(benchmark, circuit_seed):
    def circuit_comptime_compile():
        build_guppy_circuit_comptime(*circuit_seed).compile()

    benchmark.pedantic(circuit_comptime_compile, rounds=25)
