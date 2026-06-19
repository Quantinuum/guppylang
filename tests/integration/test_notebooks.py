"""Tests validating the files in the `examples` directory."""

import pytest
from pathlib import Path

example_notebooks = list(
    (Path(__file__).parent.parent.parent / "examples").glob("*.ipynb")
)

# Turn paths into strings, otherwise pytest doesn't display the names
example_notebooks = [str(f) for f in example_notebooks]

# Cells in qaoa_maxcut_example.ipynb whose outputs depend on the optimizer
# convergence path, which varies across scipy/numpy versions and platforms.
# The notebook is still executed in full — only the exact numerical outputs
# of these cells are excluded from the regression comparison.
_QAOA_STOCHASTIC_CELLS = (
    "/cells/33/outputs",  # optimizer convergence summary
    "/cells/37/outputs",  # validation success ratio
    "/cells/39/outputs",  # per-cut-value probability distribution
)


@pytest.mark.parametrize("notebook", example_notebooks)
def test_example_notebooks(nb_regression, notebook: Path):
    nb_regression.diff_ignore += (
        "/metadata/language_info/version",
        "/cells/*/outputs/*/data/image/png",
    )
    if "qaoa_maxcut_example" in str(notebook):
        nb_regression.diff_ignore += _QAOA_STOCHASTIC_CELLS
    nb_regression.check(notebook)


integration_notebooks = list((Path(__file__).parent / "notebooks").glob("*.ipynb"))


# Turn paths into strings, otherwise pytest doesn't display the names
integration_notebooks = [str(f) for f in integration_notebooks]


@pytest.mark.parametrize("notebook", integration_notebooks)
def test_integration_notebooks(nb_regression, notebook: Path):
    nb_regression.diff_ignore += ("/metadata/language_info/version",)
    nb_regression.check(notebook)
