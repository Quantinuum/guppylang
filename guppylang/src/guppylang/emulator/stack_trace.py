"""Render Selene emulator panic stack traces."""

from __future__ import annotations

from typing import TYPE_CHECKING

from guppylang_internals.diagnostic import DiagnosticsRenderer
from guppylang_internals.span import Loc, SourceMap, Span

if TYPE_CHECKING:
    from selene_sim.stack_trace import StackTrace


def render_stack_trace(stack_trace: StackTrace | None, message: str) -> str | None:
    """Render a Selene stack trace as source-annotated snippets.

    Each symbolized frame is rendered as its own code snippet. Returns `None` if no
    frame could be resolved to a readable source location, e.g. because debug info
    wasn't emitted.
    """
    if stack_trace is None:
        return None

    source = SourceMap()
    blocks: list[str] = []

    def append_frame_snippet(span: Span, label: str | None, function_name: str) -> None:
        renderer = DiagnosticsRenderer(source)
        renderer.render_snippet(
            span,
            label,
            span.end.line,
            is_primary=True,
            prefix_lines=renderer.PREFIX_ERROR_CONTEXT_LINES,
        )
        header = (
            f'File "{span.start.file}", line {span.start.line}, in {function_name}:'
        )
        blocks.append(f"{header}\n" + "\n".join(renderer.buffer))

    for entry in stack_trace.entries:
        for i, symbol in enumerate(entry.symbols):
            if symbol.filename not in source.sources:
                source.add_file(symbol.filename)
            if not source.sources[symbol.filename]:
                # Source file isn't available, skip this frame.
                continue

            loc = Loc(symbol.filename, symbol.line, symbol.column)
            span = Span(loc, loc.shift_right(1))
            append_frame_snippet(
                span, message if i == 0 else None, symbol.function_name
            )

    if not blocks:
        return None

    trace = "\n\n".join(blocks)
    indented_trace = "\n".join(f"   {line}" for line in trace.splitlines())
    return f"Guppy traceback (most recent call last):\n{indented_trace}\n"
