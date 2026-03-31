import importlib.util
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

empty_module = Path(__file__).parent / "resources/empty_module.py"
empty_module = str(empty_module.absolute().resolve())


def break_module(key) -> None:
    """Renders the module with the given key virtually unusable by replacing it with an
    empty module, causing every symbol import to fail with an ImportError."""
    spec = importlib.util.spec_from_file_location(key, empty_module)
    module = importlib.util.module_from_spec(spec)
    sys.modules[key] = module


@contextmanager
def broken_tket():
    old_modules = sys.modules.copy()

    # Break all tket and pytket imports
    for key in list(sys.modules.keys()):
        if key.startswith(("pytket", "tket")) and not key.startswith("tket_exts"):
            break_module(key)

    # Purge cached guppylang imports
    for key in list(sys.modules.keys()):
        if key.startswith("guppylang"):
            del sys.modules[key]

    try:
        yield
    finally:
        # Reset imported modules
        sys.modules = old_modules


def test_broken_tket():
    """Asserts that the module breaker works as intended to break tket imports."""

    with broken_tket(), pytest.raises(ImportError, match=r"empty_module.py"):
        from tket.circuit import Tk2Circuit  # noqa: F401


def test_broken_pytket():
    """Asserts that the module breaker works as intended to break pytket imports."""

    with broken_tket(), pytest.raises(ImportError, match=r"empty_module.py"):
        from pytket.circuit import Circuit  # noqa: F401


def test_use_pytket_decorator():
    """Tests that using the pytket decorator raises an import error when imports are
    broken."""

    with broken_tket(), pytest.raises(ImportError, match=r"empty_module.py"):  # noqa: PT012
        from guppylang import guppy

        @guppy.pytket(None)
        def f() -> None:
            pass


def test_use_load_pytket_decorator():
    """Tests that using the load_pytket decorator raises an import error when imports
    are broken."""
    with broken_tket(), pytest.raises(ImportError, match=r"empty_module.py"):  # noqa: PT012
        from guppylang import guppy

        @guppy.load_pytket("some-circuit", None)
        def f() -> None:
            pass


def test_guppy_decoupled():
    """Regression test for https://github.com/Quantinuum/guppylang/issues/1595 to
    ensure that the main guppy decorator is decoupled from the `tket` dependency, in
    that import-time problems in the `tket` dependency an import of the decorator to
    fail."""

    with broken_tket():
        from guppylang import guppy

        @guppy
        def f() -> None:
            pass

        f.check()  # Smoke test decorator
