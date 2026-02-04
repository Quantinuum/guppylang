"""Snapshot tests for miette diagnostics rendering"""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import pytest
from guppylang_internals.diagnostic import (
    Diagnostic,
    DiagnosticLevel,
    Error,
    MietteRenderer,
    Note,
)
from guppylang_internals.span import Loc, SourceMap, Span

file = "<unknown>"


def run_miette_test(source: str, diagnostic: Diagnostic, snapshot, request):
    """Helper function to run miette rendering tests with snapshots."""
    try:
        import miette_py  # noqa: F401
    except ImportError:
        pytest.skip("miette-py not available")

    sources = SourceMap()
    sources.add_file(file, source)

    renderer = MietteRenderer(sources)
    renderer.render_diagnostic(diagnostic)
    out = "\n".join(renderer.buffer)

    snapshot.snapshot_dir = str(Path(request.fspath).parent / "snapshots" / "miette")
    snapshot.assert_match(out, f"{request.node.name}.txt")


@dataclass(frozen=True)
class MyError(Error):
    title: ClassVar[str] = "Can't compare apples with oranges"
    span_label: ClassVar[str] = "Comparison attempted here"


def test_basic_diagnostic_rendering(snapshot, request):
    """Test basic diagnostic rendering matching issue #968 example."""
    source = "apple == orange"
    span = Span(Loc(file, 1, 6), Loc(file, 1, 8))
    diagnostic = MyError(span)
    run_miette_test(source, diagnostic, snapshot, request)


def test_multiple_spans_rendering(snapshot, request):
    """Test rendering with multiple span highlights (sub-diagnostics)."""

    @dataclass(frozen=True)
    class MyNote(Note):
        span_label: ClassVar[str] = "Sub-diagnostic label"

    source = "apple == orange"
    main_span = Span(Loc(file, 1, 6), Loc(file, 1, 8))
    sub_span = Span(Loc(file, 1, 9), Loc(file, 1, 15))

    diagnostic = MyError(main_span)
    diagnostic.add_sub_diagnostic(MyNote(sub_span))
    run_miette_test(source, diagnostic, snapshot, request)


def test_no_source_code_rendering(snapshot, request):
    """Test rendering diagnostics without source code (message-only)."""

    @dataclass(frozen=True)
    class NoSpanError(Error):
        title: ClassVar[str] = "Generic error"
        message: ClassVar[str] = "This is an error without source code"

    source = ""
    diagnostic = NoSpanError(None)
    run_miette_test(source, diagnostic, snapshot, request)


def test_with_help_message(snapshot, request):
    """Test miette rendering with help sub-diagnostics."""

    @dataclass(frozen=True)
    class HelpNote(Note):
        message: ClassVar[str] = "Additional sub-diagnostic message without span"

    source = "apple == orange"
    span = Span(Loc(file, 1, 6), Loc(file, 1, 8))
    diagnostic = MyError(span)
    diagnostic.add_sub_diagnostic(HelpNote(None))
    run_miette_test(source, diagnostic, snapshot, request)


def test_different_severity_levels(snapshot, request):
    """Test that different severity levels render correctly."""

    @dataclass(frozen=True)
    class WarningDiag(Error):
        title: ClassVar[str] = "Warning message"
        span_label: ClassVar[str] = "Warning here"
        level: ClassVar[DiagnosticLevel] = DiagnosticLevel.WARNING

    source = "suspicious_code()"
    span = Span(Loc(file, 1, 0), Loc(file, 1, 15))
    diagnostic = WarningDiag(span)
    run_miette_test(source, diagnostic, snapshot, request)


def test_complete_issue_example(snapshot, request):
    """Test complete example from issue #968 with primary + sub-diagnostics."""

    @dataclass(frozen=True)
    class IssueError(Error):
        title: ClassVar[str] = "Short title for the diagnostic"
        span_label: ClassVar[str] = "Primary label giving some source-dependent context"
        message: ClassVar[str] = "Optional longer message describing the error."

    @dataclass(frozen=True)
    class IssueNoteSpan(Note):
        span_label: ClassVar[str] = "Sub-diagnostic label for additional context"

    @dataclass(frozen=True)
    class IssueNoteMsg(Note):
        message: ClassVar[str] = "Additional sub-diagnostic message without span"

    # Source matching issue example structure
    source = """def hello():
    return 'world'

def foo(x: blah) -> None:
    print('function')
    x = bar() + baz"""

    # Main diagnostic on 'blah'
    main_span = Span(Loc(file, 4, 11), Loc(file, 4, 15))
    # Sub-diagnostic on 'bar()'
    sub_span = Span(Loc(file, 6, 8), Loc(file, 6, 13))

    diagnostic = IssueError(main_span)
    diagnostic.add_sub_diagnostic(IssueNoteSpan(sub_span))
    diagnostic.add_sub_diagnostic(IssueNoteMsg(None))

    run_miette_test(source, diagnostic, snapshot, request)
