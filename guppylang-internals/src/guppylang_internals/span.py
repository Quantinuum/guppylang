"""Source spans representing locations in the code being compiled."""

import ast
import linecache
from dataclasses import dataclass
from typing import TypeAlias

from guppylang_internals.ast_util import get_file, get_line_offset
from guppylang_internals.error import InternalGuppyError
from guppylang_internals.ipython_inspect import normalize_ipython_dummy_files


@dataclass(frozen=True, order=True)
class Loc:
    """A location in a source file."""

    file: str

    #: Line number starting at 1
    line: int

    #: Column number starting at 1
    column: int

    def __str__(self) -> str:
        """Returns the string representation of this source location."""
        file = normalize_ipython_dummy_files(self.file)
        return f"{file}:{self.line}:{self.column}"

    def shift_left(self, cols: int) -> "Loc":
        """Returns a new location shifted to left by the given number of columns."""
        assert self.column >= cols
        return Loc(self.file, self.line, self.column - cols)

    def shift_right(self, cols: int) -> "Loc":
        """Returns a new location shifted to right by the given number of columns."""
        return Loc(self.file, self.line, self.column + cols)


@dataclass(frozen=True)
class Span:
    """A continuous sequence of source code within a file."""

    #: Starting location of the span (inclusive)
    start: Loc

    # Ending location of the span (exclusive)
    end: Loc

    def __post_init__(self) -> None:
        if self.start.file != self.end.file:
            raise InternalGuppyError("Span: Source spans multiple files")
        if self.start > self.end:
            raise InternalGuppyError("Span: Start after end")

    def __contains__(self, x: "Span | Loc") -> bool:
        """Determines whether another span or location is completely contained in this
        span."""
        if self.file != x.file:
            return False
        if isinstance(x, Span):
            return self.start <= x.start <= self.end <= x.end
        return self.start <= x <= self.end

    def __and__(self, other: "Span") -> "Span | None":
        """Returns the intersection with the given span or `None` if they don't
        intersect."""
        if self.file != other.file:
            return None
        if self.start > other.end or other.start > self.end:
            return None
        return Span(max(self.start, other.start), min(self.end, other.end))

    def __len__(self) -> int:
        """Returns the length of a single-line span in columns.

        Querying the length of multiline spans raises an `InternalGuppyError`.
        """
        if self.is_multiline:
            raise InternalGuppyError("Span: Tried to compute length of multi-line span")
        return self.end.column - self.start.column

    @property
    def file(self) -> str:
        """The file containing this span."""
        return self.start.file

    @property
    def is_multiline(self) -> bool:
        """Whether this source sequence spans multiple lines."""
        return self.start.line != self.end.line

    def shift_left(self, cols: int) -> "Span":
        """Returns a new span that is shifted to the left by the given number of
        columns."""
        return Span(self.start.shift_left(cols), self.end.shift_left(cols))

    def shift_right(self, cols: int) -> "Span":
        """Returns a new span that is shifted to the right by the given number of
        columns."""
        return Span(self.start.shift_right(cols), self.end.shift_right(cols))


#: Objects in the compiler that are associated with a source span
ToSpan: TypeAlias = ast.AST | Span


def to_span(x: ToSpan) -> Span:
    """Extracts a source span from an object."""
    if isinstance(x, Span):
        return x
    file, line_offset = get_file(x), get_line_offset(x)
    assert file is not None
    assert line_offset is not None
    # x.lineno and line_offset both start at 1, so we have to subtract 1
    start = Loc(
        file,
        x.lineno + line_offset - 1,  # type: ignore[attr-defined]
        x.col_offset,  # type: ignore[attr-defined]
    )
    end = Loc(
        file,
        (x.end_lineno or x.lineno) + line_offset - 1,  # type: ignore[attr-defined]
        x.end_col_offset or x.col_offset,  # type: ignore[attr-defined]
    )
    return Span(start, end)


#: List of source lines in a file
SourceLines: TypeAlias = list[str]


class SourceMap:
    """Map holding the source code for all files accessed by the compiler.

    Can be used to look up the source code associated with a span.
    """

    sources: dict[str, SourceLines]

    def __init__(self) -> None:
        self.sources = {}

    def add_file(self, file: str, content: str | None = None) -> None:
        """Registers a new source file."""
        if content is None:
            self.sources[file] = [line.rstrip() for line in linecache.getlines(file)]
        else:
            self.sources[file] = content.splitlines(keepends=False)

    def span_lines(self, span: Span, prefix_lines: int = 0) -> list[str]:
        return self.sources[span.file][
            span.start.line - prefix_lines - 1 : span.end.line
        ]
