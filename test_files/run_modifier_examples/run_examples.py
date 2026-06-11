"""Compile and run modifier example HUGRs."""

# ruff: noqa: INP001, S603, T201

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
import numpy.typing as npt
from guppylang.emulator import EmulatorBuilder
from hugr.build.base import Hugr
from tket.passes import ModifierResolverPass

THIS_DIR = Path(__file__).resolve().parent
EXAMPLES_DIR = THIS_DIR.parent / "modifier_examples"
SUMMARY_PATH = THIS_DIR / "hugr_results.txt"


def format_statevector(
    state: npt.NDArray[np.complexfloating], threshold: float = 1e-6
) -> str:
    """Pretty-print a statevector, omitting amplitudes below the threshold."""
    n_qubits = int(np.round(np.log2(len(state))))
    parts = []
    for idx, amp in enumerate(state):
        if abs(amp) > threshold:
            label = format(idx, f"0{n_qubits}b")
            parts.append(f"\t{label} -> {amp:.4g}")
    return "\n".join(parts) if parts else "all amplitudes below threshold"


def example_path(name: str) -> Path:
    path = EXAMPLES_DIR / name
    return path if path.suffix == ".py" else path.with_suffix(".py")


def iter_examples(name: str | None) -> list[Path]:
    if name is not None:
        path = example_path(name)
        if not path.exists():
            raise SystemExit(f"Unknown modifier example: {name}")
        return [path]
    return sorted(EXAMPLES_DIR.glob("*.py"))


def compile_examples(paths: list[Path]) -> None:
    for path in paths:
        print(f"Re-generating {path.name}")
        subprocess.run([sys.executable, str(path)], check=True)


def run_hugrs(paths: list[Path], n_qubits: int) -> list[str]:
    resolver = ModifierResolverPass()
    all_results = []
    for source_path in paths:
        input_path = source_path.with_suffix(".hugr")
        print(f"Resolving {input_path.name}")
        hugr = Hugr.from_bytes(input_path.read_bytes())
        resolved = resolver(hugr).to_package()
        print(f"Running {input_path.name}")
        emulator = EmulatorBuilder().build(resolved, n_qubits=n_qubits)
        state = emulator.statevector_sim().run()
        result = state.partial_state_dicts()[0]["r"].as_single_state()
        all_results.append(f"{input_path.stem}:\n{format_statevector(result)}")
        print("-" * 20)
    return all_results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile and run Guppy modifier examples."
    )
    parser.add_argument(
        "example",
        nargs="?",
        help="Optional example name, with or without the .py suffix.",
    )
    parser.add_argument(
        "--skip-compile",
        action="store_true",
        help="Run existing .hugr files without regenerating them first.",
    )
    parser.add_argument(
        "--n-qubits",
        type=int,
        default=9,
        help="Number of qubits to allocate for the emulator.",
    )
    args = parser.parse_args()

    paths = iter_examples(args.example)
    if not args.skip_compile:
        compile_examples(paths)

    results = run_hugrs(sorted(EXAMPLES_DIR.glob("*.hugr")), args.n_qubits)
    SUMMARY_PATH.write_text("\n-----\n".join(results) + "\n")


if __name__ == "__main__":
    main()
