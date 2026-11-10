"""Tests optimizing Hugrs generated offline by Guppy programs."""
# ALAN TODO Should be integrated into either tests/test_optimization.py
# or tests/integration/tket_opt/

from pathlib import Path
from typing import Literal

import pytest
from hugr.build.base import Hugr
from hugr.ops import AsExtOp
from hugr.package import Package
from tket_exts import tket_registry

from tket._state import CompilationState
from tket.passes import Normalize, PytketHugrPass, QSystemRebasePass, _QSystemLLVMPass

pytket = pytest.importorskip("pytket")
from pytket.passes import CliffordSimp  # noqa: E402


def _test_files_hugr(path: Path) -> Hugr:
    with (Path(__file__).parent / "optimization" / path).open("rb") as f:
        h = Package.from_bytes(f.read(), tket_registry())
    return h.modules[0]


def _load_guppy_circuit(
    name: str,
    version_suffix: str = "",
    file_type: Literal["original", "flat", "optimized"] = "original",
) -> Hugr:
    """Load a Hugr from test_files / guppy_optimization.

    Args:
        name: Base name of the circuit (e.g., "angles", "nested_array")
        version_suffix: Version suffix (e.g., "1.1" for angles-v1.1)
        file_type: One of "original", "flat", or "optimized"

    Returns:
        Loaded HUGR module
    """
    suffix_map = {
        "original": "",
        "flat": ".flat",
        "optimized": ".opt",
    }
    suffix = suffix_map[file_type]

    dir_suffix = f"-v{version_suffix}" if version_suffix else ""

    return _test_files_hugr(Path(f"{name}{dir_suffix}") / f"{name}{suffix}.hugr")


def _count_gates(hugr: Hugr) -> dict[str, int]:
    """Returns mapping from qualified ID to count for gates and result ops only"""
    counts: dict[str, int] = {}
    for _, data in hugr.nodes():
        if isinstance(data.op, AsExtOp):
            op_name = data.op.op_def().qualified_name()
            if any(
                op_name.startswith(prefix)
                for prefix in ["tket.quantum.", "TKET1.", "tket.result."]
            ):
                counts[op_name] = counts.get(op_name, 0) + 1
    return counts


def _run_clifford_simp(hugr: Hugr) -> Hugr:
    """Apply CliffordSimp pass to a HUGR, returning the optimized HUGR."""
    clifford_pass = PytketHugrPass(CliffordSimp(allow_swaps=True))
    result = clifford_pass.run(hugr)
    return result.hugr


@pytest.mark.parametrize(
    ("name", "version_suffix", "expected"),
    [
        ("nested_array", "", None),
        # There was a significant change to angles between guppylang v1.1.x and v1.2,
        # hence the second testcase, but this only shows up when looking at rotation ops
        # - see test_angles_rotations.
        (
            "angles",
            "1.1",
            {
                "tket.quantum.MeasureFree": 1,
                "tket.quantum.QAlloc": 1,
                "tket.result.result_bool": 1,
            },
        ),
        (
            "angles",
            "",
            {
                "tket.quantum.MeasureFree": 1,
                "tket.quantum.QAlloc": 1,
                "tket.result.result_bool": 1,
            },
        ),
        (
            "simple_cx",
            "",
            {
                "tket.quantum.QAlloc": 2,
                "tket.quantum.MeasureFree": 2,
                "tket.result.result_bool": 2,
            },
        ),
        ("nested", "", None),
        ("ranges", "", None),
        (
            "false_branch",
            "",
            {
                "tket.quantum.QAlloc": 1,
                "tket.quantum.MeasureFree": 1,
                "tket.result.result_bool": 1,
            },
        ),
        (
            "func_decls",
            "",
            {"TKET1.tk1op": 2, "tket.quantum.symbolic_angle": 1},
        ),
    ],
)
def test_optimize_flattened_guppy(
    name: str, version_suffix: str, expected: dict[str, int] | None
) -> None:
    """Test that given Guppy whose control-flow has been flattened by hand,
    the optimizer can do the rest."""
    try:
        hugr = _load_guppy_circuit(name, version_suffix, "flat")
    except FileNotFoundError:
        hugr = _load_guppy_circuit(name, version_suffix, "original")

    # We don't need Normalize to "flatten" control flow here, but we still want
    # to get rid of other guppy artifacts.
    hugr = Normalize()(hugr)
    hugr = _run_clifford_simp(hugr)

    actual_counts = _count_gates(hugr)
    optimized_hugr = _load_guppy_circuit(name, version_suffix, "optimized")
    optimized_counts = _count_gates(optimized_hugr)

    if expected is not None:
        assert actual_counts != optimized_counts
        assert actual_counts == expected
        pytest.xfail()
    else:
        assert actual_counts == optimized_counts


@pytest.mark.parametrize(
    ("version_suffix", "expected"),
    [
        ("1.1", 0),  # previously working as desired
        ("", 10),  # now: https://github.com/Quantinuum/tket2/issues/2130
    ],
)
def test_angles_rotations(version_suffix, expected) -> None:
    def count_from_halfturns(hugr: Hugr) -> int:
        return sum(
            int(data.op.name().startswith("tket.rotation.from_halfturns"))
            for _, data in hugr.nodes()
        )

    hugr = _load_guppy_circuit("angles", version_suffix, "flat")
    assert count_from_halfturns(hugr) == 2

    # We don't need Normalize to "flatten" control flow here, but we still want
    # to get rid of other guppy artifacts.
    hugr = Normalize()(hugr)
    hugr = _run_clifford_simp(hugr)

    optimized = _load_guppy_circuit("angles", version_suffix, "optimized")
    assert count_from_halfturns(optimized) == 0
    assert count_from_halfturns(hugr) == expected


def test_optimize_guppy_ranges_array() -> None:
    """Demonstrates we can fully optimize the array operations in ranges.

    (i.e. after control flow is flattened, but the array ops are not)"""
    hugr = _test_files_hugr(Path("ranges") / "ranges.flat.array.hugr")

    hugr = Normalize()(hugr)
    hugr = _run_clifford_simp(hugr)

    expected_counts = _count_gates(_load_guppy_circuit("ranges", "", "optimized"))
    assert _count_gates(hugr) == expected_counts


@pytest.mark.parametrize(
    ("name", "version_suffix"),
    [
        ("nested_array", ""),
        pytest.param("angles", "1.1", marks=pytest.mark.xfail()),
        pytest.param("angles", "", marks=pytest.mark.xfail()),
        pytest.param("false_branch", "", marks=pytest.mark.xfail()),
        pytest.param("simple_cx", "", marks=pytest.mark.xfail()),
        pytest.param("nested", "", marks=pytest.mark.xfail()),
        pytest.param("ranges", "", marks=pytest.mark.xfail()),
    ],
)
def test_optimize_guppy(name: str, version_suffix: str) -> None:
    """Test full optimization pipeline on Guppy circuits.

    Check that each example optimizes to the full extent given by the .opt .hugr files,
    including lowering to QSystem.
    """
    hugr = _load_guppy_circuit(name, version_suffix, "original")

    try:
        flat_counts = _count_gates(_load_guppy_circuit(name, version_suffix, "flat"))
    except FileNotFoundError:
        flat_counts = _count_gates(hugr)

    opt_counts = _count_gates(_load_guppy_circuit(name, version_suffix, "optimized"))

    hugr = Normalize()(hugr)
    assert _count_gates(hugr) == flat_counts

    hugr = _run_clifford_simp(hugr)
    assert _count_gates(hugr) == opt_counts

    QSystemRebasePass().run(hugr)
    _QSystemLLVMPass().run(hugr)

    CompilationState.from_python(hugr).validate()
