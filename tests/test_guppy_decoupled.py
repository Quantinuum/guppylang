import importlib.util
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

broken_module = Path(__file__).parent / "resources/broken_module.py"
broken_module = str(broken_module.absolute().resolve())


def break_module(key) -> None:
    spec = importlib.util.spec_from_file_location(key, broken_module)
    module = importlib.util.module_from_spec(spec)
    sys.modules[key] = module


@contextmanager
def broken_tket():
    importlib.invalidate_caches()
    old_modules = sys.modules

    # Break all tket and pytket imports
    for key in list(sys.modules.keys()):
        if key.startswith(("pytket", "tket")):
            break_module(key)

    # Purge cached guppylang imports
    for key in list(sys.modules.keys()):
        if key.startswith("guppylang"):
            del sys.modules[key]

    yield

    # Reset imported modules
    sys.modules = old_modules
    importlib.invalidate_caches()


@pytest.mark.xfail
def test_broken_tket():
    """Asserts that the module breaker works as intended to break tket imports."""

    with broken_tket():
        from tket.circuit import Tk2Circuit  # noqa: F401


@pytest.mark.xfail
def test_broken_pytket():
    """Asserts that the module breaker works as intended to break pytket imports."""

    with broken_tket():
        from pytket.circuit import Circuit  # noqa: F401


def test_guppy_decoupled():
    """Regression test for https://github.com/Quantinuum/guppylang/issues/1595 to
    ensure that the main guppy decorator is decoupled from the `tket` dependency, in
    that import-time problems in the `tket` dependency an import of the decorator to
    fail."""

    with broken_tket():
        from guppylang import guppy  # noqa: F401
