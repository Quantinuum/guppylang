"""Tests validating the files in the `examples` directory."""

import pytest
from pathlib import Path

example_notebooks = list(
    (Path(__file__).parent.parent.parent / "examples").glob("*.ipynb")
)
# Turn paths into strings, otherwise pytest doesn't display the names
example_notebooks = [str(f) for f in example_notebooks]


@pytest.mark.parametrize("notebook", example_notebooks)
def test_example_notebooks(nb_regression, notebook: Path):
    nb_regression.diff_ignore += (
        "/metadata/language_info/version",
        "/cells/*/outputs/*/data/image/png",
    )
    nb_regression.check(notebook)


integration_notebooks = list((Path(__file__).parent / "notebooks").glob("*.ipynb"))
# Turn paths into strings, otherwise pytest doesn't display the names
integration_notebooks = [str(f) for f in integration_notebooks]


@pytest.mark.parametrize("notebook", integration_notebooks)
def test_integration_notebooks(nb_regression, notebook: Path):
    nb_regression.diff_ignore += ("/metadata/language_info/version",)
    nb_regression.check(notebook)
