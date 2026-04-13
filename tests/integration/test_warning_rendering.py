import importlib
import pathlib
import warnings

from tests.util import guppy_warning_records


def run_warning_test(file: pathlib.Path, capsys, snapshot) -> None:
    """Snapshot rich warning rendering for a module-level compiler warning."""
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        importlib.import_module(f"tests.integration.{file.parent.name}.{file.stem}")

    guppy_records = guppy_warning_records(records)
    assert len(guppy_records) == 1
    err = capsys.readouterr().err
    err = err.replace(str(file), "$FILE")

    snapshot.snapshot_dir = str(file.parent)
    snapshot.assert_match(err, file.with_suffix(".err").name)


def test_check_warning(capsys, snapshot):
    """Rich warnings should snapshot the rendered diagnostic output."""
    file = (
        pathlib.Path(__file__).parent.resolve() / "warning_cases" / "check_warning.py"
    )
    run_warning_test(file, capsys, snapshot)
