import warnings
from dataclasses import dataclass
from typing import ClassVar

import pytest
from guppylang import GuppyWarning, rich_warnings
from guppylang_internals.diagnostic import Note, Warning
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.error import diagnostic_report, emit_warning
from guppylang_internals.span import Loc, Span

file = "warning_test.py"


@dataclass(frozen=True)
class SyntheticWarning(Warning):
    title: ClassVar[str] = "Synthetic warning"
    span_label: ClassVar[str] = "Something suspicious happened"
    message: ClassVar[str] = "Additional context for the warning"


@dataclass(frozen=True)
class SyntheticNote(Note):
    message: ClassVar[str] = "Helpful note"


def make_warning() -> SyntheticWarning:
    warning = SyntheticWarning(Span(Loc(file, 3, 2), Loc(file, 3, 6)))
    warning.add_sub_diagnostic(SyntheticNote(None))
    return warning


def register_source() -> None:
    DEF_STORE.sources.add_file(file, "x = 0\nx = 1\nwarn()\n")


def test_emit_warning_with_source_location():
    """Warnings with spans should preserve filename, line, and message details."""
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        with diagnostic_report():
            emit_warning(make_warning())

    assert len(records) == 1
    warning = records[0]
    assert warning.category is GuppyWarning
    assert warning.filename == file
    assert warning.lineno == 3
    assert str(warning.message) == (
        "Synthetic warning: Something suspicious happened\n"
        "Additional context for the warning\n"
        "Note: Helpful note"
    )


def test_nested_reports_flush_on_outer_exit():
    """Nested reporting sessions should flush only when the outermost session exits."""
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        with diagnostic_report():
            with diagnostic_report():
                emit_warning(make_warning())
                assert records == []
            assert records == []

    assert len(records) == 1
    assert str(records[0].message).startswith("Synthetic warning")


def test_duplicate_warnings_are_deduplicated():
    """The same warning emitted twice in one session should only be reported once."""
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        with diagnostic_report():
            emit_warning(make_warning())
            emit_warning(make_warning())

    assert len(records) == 1


def test_warning_is_discarded_if_operation_fails():
    """Buffered warnings should be dropped if the enclosing operation raises."""

    def fail_with_warning() -> None:
        with diagnostic_report():
            emit_warning(make_warning())
            raise RuntimeError("boom")

    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        with pytest.raises(RuntimeError, match="boom"):
            fail_with_warning()

    assert len(records) == 0


def test_rich_warnings_render_to_stderr(capsys):
    """Rich warnings should preserve Python warnings and also render diagnostics."""
    register_source()
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        with rich_warnings(), diagnostic_report():
            emit_warning(make_warning())

    assert len(records) == 1
    err = capsys.readouterr().err
    assert "Warning: Synthetic warning" in err
    assert "3 |" in err
    assert "Something suspicious happened" in err


def test_nested_rich_warnings_do_not_duplicate_stderr(capsys):
    """Nested rich-warning scopes should still render exactly once."""
    register_source()
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        with rich_warnings(), rich_warnings(), diagnostic_report():
            emit_warning(make_warning())

    assert len(records) == 1
    err = capsys.readouterr().err
    assert err.count("Warning: Synthetic warning") == 1
