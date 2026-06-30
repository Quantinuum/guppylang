"""Tests validating the files in the `examples` directory."""

import pytest
from pathlib import Path

example_notebooks = list(
    (Path(__file__).parent.parent.parent / "examples").glob("*.ipynb")
)

# Turn paths into strings, otherwise pytest doesn't display the names
example_notebooks = [str(f) for f in example_notebooks]

# Per-notebook cells to exclude from regression comparison, keyed by a substring
# of the notebook filename. Values are added to nb_regression.diff_ignore when
# the key matches.
_DIFF_IGNORE_CELLS: dict[str, tuple[str, ...]] = {
    # qaoa_maxcut_example: cells whose outputs depend on optimizer convergence
    # path, which varies across scipy/numpy versions and platforms.
    "qaoa_maxcut_example": (
        "/cells/33/outputs",  # optimizer convergence summary
        "/cells/37/outputs",  # validation success ratio
        "/cells/39/outputs",  # per-cut-value probability distribution
    ),
}


@pytest.mark.parametrize("notebook", example_notebooks)
def test_example_notebooks(nb_regression, notebook: Path):
    nb_regression.diff_ignore += (
        "/metadata/language_info/version",
        "/cells/*/outputs/*/data/image/png",
    )
    for key, cells in _DIFF_IGNORE_CELLS.items():
        if key in str(notebook):
            nb_regression.diff_ignore += cells
    nb_regression.check(notebook)


integration_notebooks = list((Path(__file__).parent / "notebooks").glob("*.ipynb"))


# Turn paths into strings, otherwise pytest doesn't display the names
integration_notebooks = [str(f) for f in integration_notebooks]


@pytest.mark.parametrize("notebook", integration_notebooks)
def test_integration_notebooks(nb_regression, notebook: Path):
    nb_regression.diff_ignore += ("/metadata/language_info/version",)
    nb_regression.check(notebook)
