import importlib
import pathlib

import pytest

from guppylang import guppy


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

    snapshot.snapshot_dir = str(file.parent)
    snapshot.assert_match(stubs[module_name], file.with_suffix(".pyi").name)


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
