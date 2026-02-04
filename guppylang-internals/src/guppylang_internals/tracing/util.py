import functools
import inspect
import sys
from collections.abc import Callable
from types import FrameType, ModuleType, TracebackType
from typing import ParamSpec, TypeVar

from guppylang_internals.error import GuppyComptimeError, GuppyError, exception_hook

P = ParamSpec("P")
T = TypeVar("T")


def capture_guppy_errors(f: Callable[P, T]) -> Callable[P, T]:
    """Context manager that captures Guppy errors and turns them into runtime
    `GuppyComptimeException`s."""

    @functools.wraps(f)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return f(*args, **kwargs)
        except GuppyError as err:
            diagnostic = err.error
            msg = diagnostic.rendered_title
            if diagnostic.rendered_span_label:
                msg += f": {diagnostic.rendered_span_label}"
            if diagnostic.rendered_message:
                msg += f"\n{diagnostic.rendered_message}"
            raise GuppyComptimeError(msg) from None

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


def get_calling_frame() -> FrameType | None:
    """Finds the first frame that called this function outside the compiler."""
    frame = inspect.currentframe()
    while frame:
        module = inspect.getmodule(frame)
        if module is None or not is_compiler_module(module):
            return frame
        frame = frame.f_back
    return None


def remove_internal_frames(tb: TracebackType | None) -> TracebackType | None:
    """Removes internal frames relating to the Guppy compiler from a traceback."""
    if tb:
        module = inspect.getmodule(tb.tb_frame)
        if module is not None and is_compiler_module(module):
            return remove_internal_frames(tb.tb_next)
        if tb.tb_next:
            tb.tb_next = remove_internal_frames(tb.tb_next)
    return tb


def is_compiler_module(module: ModuleType) -> bool:
    """Checks whether a given Python module belongs to the Guppy compiler."""
    return module.__name__.startswith(
        "guppylang_internals."
    ) or module.__name__.startswith("guppylang.")
