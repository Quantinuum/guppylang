import importlib
import importlib.util
import importlib.machinery
import pathlib
import sys
import types
from pathlib import Path

import pytest

from guppylang import guppy


def import_from_path(
    module_name: str, file_path: Path
) -> tuple[types.ModuleType, importlib.machinery.ModuleSpec]:
    loader = importlib.machinery.SourceFileLoader(module_name, str(file_path))
    spec = importlib.util.spec_from_file_location(
        module_name, str(file_path), loader=loader
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    return module, spec


def _run_stub_test(file, snapshot):
    file = pathlib.Path(file)

    module_name = f"tests.integration.stub.{file.stem}"
    module = importlib.import_module(module_name)
    # Collect top level functions defined in the module
    library = guppy.library(
        *[item for name, item in module.__dict__.items() if name.startswith("lib_")],
    )
    library.check()
    stubs = library.stubs()

    assert module_name in stubs, f"Expected stubs to be generated for {module_name}"
    assert len(stubs) == 1, (
        "Expected exactly one stub module to be generated, but got: "
        + ", ".join(stubs.keys())
    )

    stub_file = file.with_suffix(".pyi")
    snapshot.snapshot_dir = str(file.parent)
    snapshot.assert_match(stubs[module_name], stub_file.name)

    # Test whether stubs can be imported, e.g. to test whether all required names are
    # defined in import statements.
    module, spec = import_from_path(file.stem, stub_file.resolve())
    try:
        spec.loader.exec_module(module)
    except Exception as e:  # noqa: BLE001
        pytest.fail(
            f"Type stubs were generated, but are bad! Exception during import: {e!s}"
        )


path = pathlib.Path(__file__).parent.resolve() / "stub"
files = [
    x
    for x in path.iterdir()
    if x.is_file() and x.suffix == ".py" and x.name != "__init__.py"
]

# Turn paths into strings, otherwise pytest doesn't display the names
files = [str(f) for f in files]


@pytest.mark.parametrize("file", files)
def test_stubs(file, snapshot):
    _run_stub_test(file, snapshot)
