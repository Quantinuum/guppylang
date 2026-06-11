"""Resolve modifier ops in modifier example HUGRs."""

# ruff: noqa: INP001, T201

from __future__ import annotations

import sys
from pathlib import Path

from hugr.build.base import Hugr
from tket.passes import ModifierResolverPass

THIS_DIR = Path(__file__).resolve().parent
EXAMPLES_DIR = THIS_DIR.parent / "modifier_examples"
MODIFIED_HUGRS_DIR = THIS_DIR / "modified_hugrs"


def apply_passes(input_paths: list[Path], output_dir: Path) -> None:
    resolver = ModifierResolverPass()
    output_dir.mkdir(parents=True, exist_ok=True)
    for input_path in input_paths:
        print(f"Resolving {input_path.name}")
        hugr = Hugr.from_bytes(input_path.read_bytes())
        resolved = resolver(hugr)
        output_path = output_dir / f"{input_path.stem}_solved.hugr"
        output_path.write_bytes(resolved.to_bytes())


def main() -> None:
    input_paths = (
        [EXAMPLES_DIR / f"{sys.argv[1]}.hugr"]
        if len(sys.argv) > 1
        else sorted(EXAMPLES_DIR.glob("*.hugr"))
    )
    apply_passes(input_paths, MODIFIED_HUGRS_DIR)


if __name__ == "__main__":
    main()
