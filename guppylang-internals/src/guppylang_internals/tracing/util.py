import functools
import sys
from collections.abc import Callable
from types import TracebackType
from typing import ParamSpec, TypeVar

from guppylang_internals.error import GuppyComptimeError, GuppyError, exception_hook
from guppylang_internals.frame_util import remove_internal_frames

P = ParamSpec("P")
T = TypeVar("T")


class capture_guppy_errors:
    """Context manager that captures Guppy errors and turns them into runtime
    `GuppyComptimeError`s.

    Also allows usage as a decorator.
    """

    # Note: Ideally, this would have been defined using the `contextlib.contextmanager`
    # decorator, however this would interact badly with `@hide_trace` below since we
    # would be inserting additional stack frames into the Python standard library.

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if isinstance(exc_val, GuppyError):
            diagnostic = exc_val.error
            msg = diagnostic.rendered_title
            if diagnostic.rendered_span_label:
                msg += f": {diagnostic.rendered_span_label}"
            if diagnostic.rendered_message:
                msg += f"\n{diagnostic.rendered_message}"
            # Reraise the exception as a comptime error. Note the `from None` which
            # erases the exception context so the user doesn't see an additional note in
            # the traceback.
            raise GuppyComptimeError(msg) from None

    def __call__(self, f: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(f)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
            with self:
                return f(*args, **kwargs)

        return wrapped


def hide_trace(f: Callable[P, T]) -> Callable[P, T]:
    """Function decorator that hides compiler-internal frames from the traceback of any
    exception thrown by the decorated function."""

    @functools.wraps(f)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        with exception_hook(tracing_except_hook):
            return f(*args, **kwargs)

    return wrapped


def tracing_except_hook(
    excty: type[BaseException], err: BaseException, traceback: TracebackType | None
) -> None:
    """Except hook that removes all compiler-internal frames from the traceback."""
    traceback = remove_internal_frames(traceback)
    try:
        # Check if we're inside a jupyter notebook since it uses its own exception
        # hook. If we're in a regular interpreter, this line will raise a `NameError`
        ipython_shell = get_ipython()  # type: ignore[name-defined]
        ipython_shell.excepthook(excty, err, traceback)
    except NameError:
        sys.__excepthook__(excty, err, traceback)
