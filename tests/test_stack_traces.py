"""Snapshot tests for emulator panic stack traces."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from guppylang.emulator import EmulatorError

TEST_CASES_DIR = Path(__file__).parent / "stack_traces"
FILES = [
    path
    for path in TEST_CASES_DIR.glob("*.py")
    if path.name != "__init__.py" and path.name != "test_helper.py"
]


@pytest.mark.parametrize("file", FILES)
def test_stack_trace(file: Path, snapshot: pytest.Snapshot) -> None:
    with pytest.raises(EmulatorError) as exc_info:
        importlib.import_module(f"tests.stack_traces.{file.stem}")

    output = str(exc_info.value).replace(str(TEST_CASES_DIR.resolve()), "$PATH_TO_FILE")
    snapshot.snapshot_dir = str(file.parent)
    snapshot.assert_match(output + "\n", file.with_suffix(".err").name)
