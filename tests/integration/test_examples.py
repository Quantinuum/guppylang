"""Tests validating the files in the `examples` directory."""

import pytest
from pathlib import Path

notebook_files = list(
    (Path(__file__).parent.parent.parent / "examples").glob("*.ipynb")
)

# Remove long running QAOA notebook from C.I. tests
# Hopefully we can add it back in when we can speed it up.
notebook_files.remove(
    Path("/home/runner/work/guppylang/guppylang/examples/qaoa_maxcut_example.ipynb")
)


@pytest.mark.parametrize("notebook", notebook_files)
def test_example_notebooks(nb_regression, notebook: Path):
    nb_regression.diff_ignore += (
        "/metadata/language_info/version",
        "/cells/*/outputs/*/data/image/png",
    )
    nb_regression.check(notebook)


def test_demo_notebook(nb_regression):
    nb_regression.diff_ignore += ("/metadata/language_info/version",)
    nb_regression.check("tests/integration/notebooks/demo.ipynb")


def test_comptime_notebook(nb_regression):
    nb_regression.diff_ignore += ("/metadata/language_info/version",)
    nb_regression.check("tests/integration/notebooks/comptime.ipynb")


def test_misc_notebook_tests(nb_regression):
    nb_regression.diff_ignore += ("/metadata/language_info/version",)
    nb_regression.check("tests/integration/notebooks/misc_notebook_tests.ipynb")
