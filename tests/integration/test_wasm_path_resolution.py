"""Tests for WASM file path resolution (issue #1407).

Verifies that @wasm_module resolves relative paths relative to the source file
containing the decorator, not the current working directory.
"""

from pathlib import Path

import pytest

from guppylang import guppy
from guppylang_internals.decorator import wasm, wasm_module
from guppylang_internals.error import GuppyError
from guppylang.std.qsystem.wasm import spawn_wasm_contexts


RESOURCES_DIR = Path(__file__).resolve().parent.parent / "resources"
WASM_FILE = str(RESOURCES_DIR / "test.wasm")


def test_relative_path_from_different_cwd(validate, monkeypatch, tmp_path):
    """A module using @wasm_module with a relative path should work even when
    the process cwd differs from the module's directory (issue #1407)."""
    # Change cwd to a directory that does NOT contain the wasm file
    monkeypatch.chdir(tmp_path)

    # Import a module that uses @wasm_module("test.wasm") with a relative path.
    # The wasm file lives next to that module, not in tmp_path.
    from tests.resources.wasm_subdir.wasm_defs import RelativeWasm

    @guppy
    def main() -> int:
        [mod] = spawn_wasm_contexts(1, RelativeWasm)
        a = mod.two()
        b = mod.add(a, a)
        mod.discard()
        return b

    mod = main.compile_function()
    validate(mod)


def test_absolute_path(validate):

    @wasm_module(WASM_FILE)
    class AbsWasm:
        @wasm
        def two(self: "AbsWasm") -> int: ...

    @guppy
    def main() -> int:
        [mod] = spawn_wasm_contexts(1, AbsWasm)
        x = mod.two()
        mod.discard()
        return x

    mod = main.compile_function()
    validate(mod)


def test_absolute_path_unaffected_by_cwd(validate, monkeypatch, tmp_path):
    """Absolute paths should work even when cwd is changed."""
    monkeypatch.chdir(tmp_path)

    @wasm_module(WASM_FILE)
    class AbsWasm:
        @wasm
        def two(self: "AbsWasm") -> int: ...

    @guppy
    def main() -> int:
        [mod] = spawn_wasm_contexts(1, AbsWasm)
        x = mod.two()
        mod.discard()
        return x

    mod = main.compile_function()
    validate(mod)


def test_nonexistent_relative_path_error():
    """A relative path that doesn't exist should still raise WasmFileNotFound."""
    with pytest.raises(GuppyError):

        @wasm_module("no_such_file.wasm")
        class BadWasm:
            pass
