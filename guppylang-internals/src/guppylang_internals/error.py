import functools
import sys
import warnings
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from types import TracebackType
from typing import TYPE_CHECKING, Any, NamedTuple, TypeVar, cast

if TYPE_CHECKING:
    from guppylang_internals.diagnostic import Diagnostic, Error, Fatal


@dataclass
class GuppyError(Exception):
    """An error that occurs during compilation."""

    error: "Error | Fatal"


class GuppyTypeError(GuppyError):
    """Special Guppy exception for type errors."""


class GuppyTypeInferenceError(GuppyError):
    """Special Guppy exception for type inference errors."""


class MissingModuleError(Exception):
    """Special Guppy exception for operations that require a guppy module."""


class GuppyComptimeError(Exception):
    """Exception for type and linearity errors that are caught in a comptime context."""


class RequiresMonomorphizationError(Exception):
    """Internal exception that is used whenever type checking cannot proceed without
    monomorphizaion.

    When checking generic functions, we first try a pass where the parameters are kept
    as opaque variables to give nicer error messaged. This exception is thrown whenever
    we cannot proceed using only opaque values.
    """


class InternalGuppyError(Exception):
    """Exception for internal problems during compilation."""


class GuppyWarning(UserWarning):
    """Warning category for non-fatal compiler diagnostics."""


ExceptHook = Callable[[type[BaseException], BaseException, TracebackType | None], Any]


class WarningKey(NamedTuple):
    """Stable identity for deduplicating warnings within one operation."""

    filename: str | None
    lineno: int | None
    column: int | None
    message: str


@dataclass(frozen=True)
class PendingWarning:
    """Buffered warning waiting to be emitted at the end of a top-level operation."""

    diagnostic: "Diagnostic"
    message: str
    filename: str | None
    lineno: int | None
    key: WarningKey


@dataclass
class DiagnosticSession:
    """Per-operation diagnostic state shared across nested compiler calls."""

    rich_warnings: bool = False
    pending_warnings: list[PendingWarning] = field(default_factory=list)
    seen_warnings: set[WarningKey] = field(default_factory=set)


_DIAGNOSTIC_SESSION: ContextVar[DiagnosticSession | None] = ContextVar(
    "_DIAGNOSTIC_SESSION", default=None
)
_RICH_WARNINGS: ContextVar[bool] = ContextVar("_RICH_WARNINGS", default=False)


@contextmanager
def exception_hook(hook: ExceptHook) -> Iterator[None]:
    """Sets a custom `excepthook` for the scope of a 'with' block."""
    try:
        # Check if we're inside a jupyter notebook since it uses its own exception
        # hook. If we're in a regular interpreter, this line will raise a `NameError`
        ipython_shell = (
            get_ipython()  # type: ignore[name-defined] # pyright: ignore[reportUndefinedVariable]
        )

        def ipython_excepthook(
            shell: Any,
            etype: type[BaseException],
            value: BaseException,
            tb: TracebackType | None,
            tb_offset: Any = None,
        ) -> Any:
            return hook(etype, value, tb)

        old_hook = ipython_shell.CustomTB
        old_exc_tuple = ipython_shell.custom_exceptions
        ipython_shell.set_custom_exc((Exception,), ipython_excepthook)
        yield
        ipython_shell.CustomTB = old_hook
        ipython_shell.custom_exceptions = old_exc_tuple
    except NameError:
        pass
    else:
        return

    # Otherwise, override the regular sys.excepthook
    old_hook = sys.excepthook
    sys.excepthook = hook
    yield
    sys.excepthook = old_hook


@contextmanager
def saved_exception_hook() -> Iterator[None]:
    """Restores `sys.excepthook` to its current value after the 'with' block exits.

    Unlike `exception_hook`, this does not install a new hook — it simply guarantees
    that any changes made inside the block (e.g. by `@hide_trace`-decorated callables)
    are rolled back when the block exits, whether normally or via an exception.
    """
    old_hook = sys.excepthook
    try:
        yield
    finally:
        sys.excepthook = old_hook


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

    if pending_warning.key in session.seen_warnings:
        # Re-emitting the same warning from nested passes or revisited CFG nodes should
        # not duplicate the user-facing Python warning within one operation.
        return

    session.seen_warnings.add(pending_warning.key)
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
        message=message,
        filename=filename,
        lineno=lineno,
        # Deduplicate on source location plus rendered message so repeated reports from
        # the same site collapse, while distinct warnings on one line still survive.
        key=WarningKey(filename, lineno, column, message),
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


FuncT = TypeVar("FuncT", bound=Callable[..., Any])


def pretty_errors(f: FuncT) -> FuncT:
    """Decorator to print custom error banners when a `GuppyError` occurs.

    This is also the standard boundary for warning collection on top-level engine
    operations: wrapped calls participate in one `diagnostic_report()` session.
    """

    def hook(
        excty: type[BaseException], err: BaseException, traceback: TracebackType | None
    ) -> None:
        """Custom `excepthook` that intercepts `GuppyExceptions` for pretty printing."""
        if isinstance(err, GuppyError):
            from guppylang_internals.diagnostic import DiagnosticsRenderer
            from guppylang_internals.engine import DEF_STORE

            renderer = DiagnosticsRenderer(DEF_STORE.sources)
            renderer.render_diagnostic(err.error)
            sys.stderr.write("\n".join(renderer.buffer))
            sys.stderr.write("\n\nGuppy compilation failed due to 1 previous error\n")
            return

        # If it's not a GuppyError, fall back to default hook
        sys.__excepthook__(excty, err, traceback)

    @functools.wraps(f)
    def pretty_errors_wrapped(*args: Any, **kwargs: Any) -> Any:
        with diagnostic_report(), exception_hook(hook):
            return f(*args, **kwargs)

    return cast("FuncT", pretty_errors_wrapped)
