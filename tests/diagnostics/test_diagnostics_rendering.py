"""Snapshot tests for diagnostics rendering"""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from guppylang_internals.diagnostic import (
    Diagnostic,
    DiagnosticsRenderer,
    Error,
    Help,
    Note,
)
from guppylang_internals.span import Loc, SourceMap, Span

file = "<unknown>"


def run_test(source: str, diagnostic: Diagnostic, snapshot, request):
    sources = SourceMap()
    sources.add_file(file, source)

    renderer = DiagnosticsRenderer(sources)
    renderer.render_diagnostic(diagnostic)
    out = "\n".join(renderer.buffer)

    snapshot.snapshot_dir = str(Path(request.fspath).parent / "snapshots")
    snapshot.assert_match(out, f"{request.node.name}.txt")


@dataclass(frozen=True)
class MyError(Error):
    title: ClassVar[str] = "Can't compare apples with oranges"
    span_label: ClassVar[str] = "Comparison attempted here"


def test_only_title(snapshot, request):
    @dataclass(frozen=True)
    class MyDiagnostic(Error):
        title: ClassVar[str] = "Can't compare apples with oranges"

    source = ""
    diagnostic = MyDiagnostic(None)
    run_test(source, diagnostic, snapshot, request)


def test_only_message(snapshot, request):
    @dataclass(frozen=True)
    class MyDiagnostic(Error):
        title: ClassVar[str] = "Can't compare apples with oranges"
        message: ClassVar[str] = (
            "Can't compare apples with oranges. Please refer to Barone (BMJ, 2000), "
            "https://doi.org/10.1136%2Fbmj.321.7276.1569 for further details."
        )

    source = ""
    diagnostic = MyDiagnostic(None)
    run_test(source, diagnostic, snapshot, request)


def test_only_label(snapshot, request):
    source = "apple == orange"
    span = Span(Loc(file, 1, 6), Loc(file, 1, 8))
    diagnostic = MyError(span)
    run_test(source, diagnostic, snapshot, request)


def test_message_with_span(snapshot, request):
    @dataclass(frozen=True)
    class MyDiagnostic(Error):
        title: ClassVar[str] = "Can't compare apples with oranges"
        message: ClassVar[str] = (
            "Please refer to Barone (BMJ, 2000), "
            "https://doi.org/10.1136%2Fbmj.321.7276.1569 for further details."
        )

    source = "apple == orange"
    span = Span(Loc(file, 1, 6), Loc(file, 1, 8))
    diagnostic = MyDiagnostic(span)
    run_test(source, diagnostic, snapshot, request)


def test_three_labels_formatted(snapshot, request):
    @dataclass(frozen=True)
    class MySubDiagnostic(Note):
        thing: str
        span_label: ClassVar[str] = "This is an {thing}"

    source = "apple == orange"
    span = Span(Loc(file, 1, 6), Loc(file, 1, 8))
    span_apple = Span(Loc(file, 1, 0), Loc(file, 1, 5))
    span_orange = Span(Loc(file, 1, 9), Loc(file, 1, 15))
    diagnostic = MyError(span)
    diagnostic.add_sub_diagnostic(MySubDiagnostic(span_apple, "apple"))
    diagnostic.add_sub_diagnostic(MySubDiagnostic(span_orange, "orange"))
    run_test(source, diagnostic, snapshot, request)


def test_advanced_formatting(snapshot, request):
    @dataclass(frozen=True)
    class MyDiagnostic(Error):
        title: ClassVar[str] = "Can't compare apples with oranges"
        span_label: ClassVar[str] = "This is an {a}{pp}{le}"
        a: str

        @property
        def pp(self) -> str:
            return "pp"

        @property
        def le(self) -> str:
            return "le"

    @dataclass(frozen=True)
    class MySubDiagnostic(Note):
        span_label: ClassVar[str] = "This is not an {a}{pp}{p}{le}"
        p: str

        @property
        def pp(self) -> str:
            return "p"

    source = "apple == orange"
    span_apple = Span(Loc(file, 1, 0), Loc(file, 1, 5))
    span_orange = Span(Loc(file, 1, 9), Loc(file, 1, 15))
    diagnostic = MyDiagnostic(span_apple, "a")
    diagnostic.add_sub_diagnostic(MySubDiagnostic(span_orange, "p"))
    run_test(source, diagnostic, snapshot, request)


def test_long_label(snapshot, request):
    @dataclass(frozen=True)
    class MyDiagnostic(Error):
        title: ClassVar[str] = "Can't compare apples with oranges"
        span_label: ClassVar[str] = "Comparison attempted here. " * 20

    source = "apple == orange"
    span = Span(Loc(file, 1, 6), Loc(file, 1, 8))
    diagnostic = MyDiagnostic(span)
    run_test(source, diagnostic, snapshot, request)


def test_help(snapshot, request):
    @dataclass(frozen=True)
    class MySubDiagnostic(Help):
        message: ClassVar[str] = "Have you tried peeling the orange?"

    source = "apple == orange"
    span = Span(Loc(file, 1, 6), Loc(file, 1, 8))
    diagnostic = MyError(span)
    diagnostic.add_sub_diagnostic(MySubDiagnostic(None))
    run_test(source, diagnostic, snapshot, request)


def test_note(snapshot, request):
    @dataclass(frozen=True)
    class MySubDiagnostic(Note):
        message: ClassVar[str] = "Stop trying, this is a fruitless endeavor"

    source = "apple == orange"
    span = Span(Loc(file, 1, 6), Loc(file, 1, 8))
    diagnostic = MyError(span)
    diagnostic.add_sub_diagnostic(MySubDiagnostic(None))
    run_test(source, diagnostic, snapshot, request)


def test_context(snapshot, request):
    source = "super_apple := apple ** 2\nlemon := orange - apple\napple == orange"
    span = Span(Loc(file, 3, 6), Loc(file, 3, 8))
    diagnostic = MyError(span)
    run_test(source, diagnostic, snapshot, request)


def test_justify_line_number(snapshot, request):
    source = "foo\n" * 99 + "apple == orange"
    span = Span(Loc(file, 100, 6), Loc(file, 100, 8))
    diagnostic = MyError(span)
    run_test(source, diagnostic, snapshot, request)


def test_two_spans_different_lineno_lens(snapshot, request):
    @dataclass(frozen=True)
    class MySubDiagnostic(Note):
        span_label: ClassVar[str] = "This is an apple"

    source = 99 * "apple == orange\n" + "This apple is on another line"
    span1 = Span(Loc(file, 99, 6), Loc(file, 99, 8))
    span2 = Span(Loc(file, 100, 5), Loc(file, 100, 10))
    diagnostic = MyError(span1)
    diagnostic.add_sub_diagnostic(MySubDiagnostic(span2))
    run_test(source, diagnostic, snapshot, request)


def test_indented(snapshot, request):
    source = " " * 50 + "super_apple := apple ** 2\n"
    source += " " * 50 + "    lemon := orange - apple\n"
    source += " " * 50 + "        apple == orange"
    span = Span(Loc(file, 3, 50 + 8 + 6), Loc(file, 3, 50 + 8 + 8))
    diagnostic = MyError(span)
    run_test(source, diagnostic, snapshot, request)


def test_two_line_span(snapshot, request):
    source = "apple.compare(\n     orange) == EQUAL"
    span = Span(Loc(file, 1, 5), Loc(file, 2, 12))
    diagnostic = MyError(span)
    run_test(source, diagnostic, snapshot, request)


def test_three_line_span(snapshot, request):
    source = "apple.compare(\n     orange\n) == EQUAL"
    span = Span(Loc(file, 1, 5), Loc(file, 3, 1))
    diagnostic = MyError(span)
    run_test(source, diagnostic, snapshot, request)


def test_message_new_line(snapshot, request):
    @dataclass(frozen=True)
    class MyError(Error):
        message: ClassVar[str] = "Apple " * 20 + "\n\n" + "Orange " * 30

    diagnostic = MyError(None)
    run_test("", diagnostic, snapshot, request)


def test_far_indented_label(snapshot, request):
    @dataclass(frozen=True)
    class MyDiagnostic(Error):
        title: ClassVar[str] = "Can't compare apples with oranges"
        span_label: ClassVar[str] = "Comparison attempted here. " * 20

    source = "apple + " * 10 + "apple == orange"
    span = Span(Loc(file, 1, 86), Loc(file, 1, 88))
    diagnostic = MyDiagnostic(span)
    run_test(source, diagnostic, snapshot, request)


def test_leading_tab_characters_single_line_span(snapshot, request):
    source = "\tsuper_apple := apple ** 2\n"
    source += "\tlemon := orange - apple\n"
    source += "\tapple == orange\n"
    span = Span(Loc(file, 3, 1), Loc(file, 3, 1 + 15))
    diagnostic = MyError(span)
    run_test(source, diagnostic, snapshot, request)


def test_leading_tab_characters_multi_line_span(snapshot, request):
    source = "\tsuper_apple := apple ** 2\n"
    source += "\tlemon := orange - apple\n"
    source += "\tapple == orange\n"
    span = Span(Loc(file, 1, 1), Loc(file, 3, 1 + 15))
    diagnostic = MyError(span)
    run_test(source, diagnostic, snapshot, request)


def test_leading_tab_characters_multi_line_span_varying_tabs(snapshot, request):
    source = "\t\tsuper_apple := apple ** 2\n"
    source += "\tlemon := orange - apple\n"
    source += "\t\t\tapple == orange\n"
    span = Span(Loc(file, 1, 2), Loc(file, 3, 3 + 15))
    diagnostic = MyError(span)
    run_test(source, diagnostic, snapshot, request)
