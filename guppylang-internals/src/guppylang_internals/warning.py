import sys
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, NamedTuple

from guppylang_internals.error import InternalGuppyError

if TYPE_CHECKING:
    from guppylang_internals.diagnostic import Diagnostic


class GuppyWarning(UserWarning):
    """Warning category for non-fatal compiler diagnostics."""


class _WarningKey(NamedTuple):
    """Stable identity for deduplicating warnings within one operation."""

    # File path passed through to Python's warning machinery, if available.
    filename: str | None
    # 1-based source line passed through to Python's warning machinery, if available.
    lineno: int | None
    # 0-based source column used only for deduplicating distinct warnings on one line.
    column: int | None
    # Concise warning text emitted through Python's warning machinery.
    message: str


@dataclass(frozen=True)
class PendingWarning:
    """Buffered warning waiting to be emitted at the end of a top-level operation."""

    # Original structured diagnostic used for rich rendering.
    diagnostic: "Diagnostic"
    # Stable warning identity and Python-warning payload.
    _key: _WarningKey

    @property
    def message(self) -> str:
        """Concise warning text emitted through Python's warning machinery."""
        return self._key.message

    @property
    def filename(self) -> str | None:
        """Source file reported to Python's warning machinery, if available."""
        return self._key.filename

    @property
    def lineno(self) -> int | None:
        """1-based source line reported to Python's warning machinery, if available."""
        return self._key.lineno

    @property
    def column(self) -> int | None:
        """0-based source column used for deduplication within one operation."""
        return self._key.column


@dataclass
class DiagnosticSession:
    """Per-operation diagnostic state shared across nested compiler calls."""

    rich_warnings: bool = False
    pending_warnings: list[PendingWarning] = field(default_factory=list)
    seen_warnings: set[_WarningKey] = field(default_factory=set)


_DIAGNOSTIC_SESSION: ContextVar[DiagnosticSession | None] = ContextVar(
    "_DIAGNOSTIC_SESSION", default=None
)
_RICH_WARNINGS: ContextVar[bool] = ContextVar("_RICH_WARNINGS", default=False)


@contextmanager
def rich_warnings() -> Iterator[None]:
    """Enable rich stderr rendering for compiler warnings within the current scope."""

    token = _RICH_WARNINGS.set(True)
    try:
        yield
    finally:
        _RICH_WARNINGS.reset(token)


@contextmanager
def diagnostic_report() -> Iterator[None]:
    """Collects compiler warnings and flushes them once per top-level operation."""

    session = _DIAGNOSTIC_SESSION.get()
    # Nested compiler entrypoints reuse the same session so one user operation only
    # flushes once, at the outermost boundary.
    outermost = session is None
    token = None
    if outermost:
        session = DiagnosticSession(rich_warnings=_RICH_WARNINGS.get())
        token = _DIAGNOSTIC_SESSION.set(session)
    assert session is not None

    try:
        yield
    except Exception:
        if outermost:
            # Failed operations should not emit queued warnings. Clear eagerly so the
            # exception path behaves the same whether the warning producer ran before
            # or after the eventual failure.
            session.pending_warnings.clear()
            session.seen_warnings.clear()
        raise
    else:
        if outermost:
            # Only the outermost context flushes to Python warnings. Inner contexts
            # merely contribute to the shared session.
            for pending_warning in session.pending_warnings:
                _emit_pending_warning(pending_warning)
    finally:
        if outermost and token is not None:
            # Restore the previous ContextVar value even if warning emission itself
            # raises, so subsequent compiler operations start with a clean session.
            _DIAGNOSTIC_SESSION.reset(token)


def emit_warning(diag: "Diagnostic") -> None:
    """Queue or emit a non-fatal compiler warning."""

    pending_warning = _pending_warning(diag)
    session = _DIAGNOSTIC_SESSION.get()
    if session is None:
        # Warnings emitted outside a diagnostic_report block still surface
        # immediately; the session machinery is only needed for batching and
        # deduplicating within top-level compiler operations.
        _emit_pending_warning(pending_warning)
        return

    if pending_warning._key in session.seen_warnings:
        # Re-emitting the same warning from nested passes or revisited CFG nodes should
        # not duplicate the user-facing Python warning within one operation.
        return

    session.seen_warnings.add(pending_warning._key)
    session.pending_warnings.append(pending_warning)


def _pending_warning(diag: "Diagnostic") -> PendingWarning:
    from guppylang_internals.diagnostic import DiagnosticLevel
    from guppylang_internals.span import to_span

    if diag.level is not DiagnosticLevel.WARNING:
        raise InternalGuppyError("emit_warning expects a warning-level diagnostic")

    filename = None
    lineno = None
    column = None
    if diag.span is not None:
        # Python's warning machinery wants file/line information separately rather
        # than Guppy's richer span object.
        span = to_span(diag.span)
        filename = span.start.file
        lineno = span.start.line
        column = span.start.column

    message = _warning_message(diag)
    return PendingWarning(
        diagnostic=diag,
        # Deduplicate on source location plus rendered message so repeated reports from
        # the same site collapse, while distinct warnings on one line still survive.
        _key=_WarningKey(filename, lineno, column, message),
    )


def _emit_pending_warning(pending_warning: PendingWarning) -> None:
    """Emit one queued warning via Python's warning machinery and rich stderr output."""

    if pending_warning.filename is not None and pending_warning.lineno is not None:
        warnings.warn_explicit(
            pending_warning.message,
            GuppyWarning,
            pending_warning.filename,
            pending_warning.lineno,
        )
    else:
        warnings.warn(
            pending_warning.message,
            GuppyWarning,
            stacklevel=2,
        )

    session = _DIAGNOSTIC_SESSION.get()
    if session is not None and session.rich_warnings:
        sys.stderr.write(_render_warning(pending_warning))
        sys.stderr.write("\n")


def _render_warning(pending_warning: PendingWarning) -> str:
    from guppylang_internals.diagnostic import DiagnosticsRenderer
    from guppylang_internals.engine import DEF_STORE

    renderer = DiagnosticsRenderer(DEF_STORE.sources)
    try:
        renderer.render_diagnostic(pending_warning.diagnostic)
    except KeyError:
        return pending_warning.message
    return "\n".join(renderer.buffer)


def _warning_message(diag: "Diagnostic") -> str:
    lines = [diag.rendered_title]
    if diag.rendered_span_label:
        lines[0] += f": {diag.rendered_span_label}"
    if diag.rendered_message:
        lines.append(diag.rendered_message)
    lines.extend(
        [
            f"{child.level.name.lower().capitalize()}: {child.rendered_message}"
            for child in diag.children
            if child.rendered_message
        ]
    )
    return "\n".join(lines)
