import functools
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from guppylang_internals.diagnostic import Error, Fatal


@dataclass
class GuppyError(Exception):
    """An error that occurs during compilation."""

    error: "Error | Fatal"

    def __str__(self) -> str:
        from guppylang_internals.diagnostic import DiagnosticsRenderer
        from guppylang_internals.engine import DEF_STORE

        renderer = DiagnosticsRenderer(DEF_STORE.sources)
        renderer.render_diagnostic(self.error)
        return (
            "\n".join(renderer.buffer)
            + "\n\nGuppy compilation failed due to 1 previous error\n"
        )


class GuppyTypeError(GuppyError):
    """Special Guppy exception for type errors."""


class GuppyTypeInferenceError(GuppyError):
    """Special Guppy exception for type inference errors."""


class BypassOverloadError(GuppyError):
    """A Guppy error that should bypass overload error suppression."""


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


ExceptHook = Callable[[type[BaseException], BaseException, TracebackType | None], Any]


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


def pretty_errors[**P, T](f: Callable[P, T]) -> Callable[P, T]:
    """Decorator to print custom error banners when a `GuppyError` occurs."""

    def hook(
        excty: type[BaseException], err: BaseException, traceback: TracebackType | None
    ) -> None:
        """Custom `excepthook` that intercepts `GuppyExceptions` for pretty printing."""
        if isinstance(err, GuppyError):
            sys.stderr.write(str(err))
            return

        # If it's not a GuppyError, fall back to default hook
        sys.__excepthook__(excty, err, traceback)

    @functools.wraps(f)
    def pretty_errors_wrapped(*args: Any, **kwargs: Any) -> Any:
        with exception_hook(hook):
            return f(*args, **kwargs)

    return cast("Callable[P, Any]", pretty_errors_wrapped)
