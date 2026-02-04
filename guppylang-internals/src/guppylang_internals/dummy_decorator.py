from typing import Any, TypeVar


class _DummyGuppy:
    """A dummy class with the same interface as `@guppy` that does nothing when used to
    decorate functions.

    We use this during sphinx builds as a mock for the decorator, to ensure that Guppy
    functions are recognised as regular functions and included in docs.
    """

    def __call__(self, f: Any) -> Any:
        return f

    def comptime(self, f: Any) -> Any:
        return f

    def extend_type(self, *args: Any, **kwargs: Any) -> Any:
        return lambda cls: cls

    def type(self, *args: Any, **kwargs: Any) -> Any:
        return lambda cls: cls

    def struct(self, cls: Any) -> Any:
        return cls

    def type_var(self, name: str, *args: Any, **kwargs: Any) -> Any:
        return TypeVar(name)

    def nat_var(self, name: str, *args: Any, **kwargs: Any) -> Any:
        return TypeVar(name)

    def custom(self, *args: Any, **kwargs: Any) -> Any:
        return lambda f: f

    def hugr_op(self, *args: Any, **kwargs: Any) -> Any:
        return lambda f: f

    def declare(self, f: Any) -> Any:
        return f

    def overload(self, *args: Any, **kwargs: Any) -> Any:
        return lambda f: f

    def constant(self, *args: Any, **kwargs: Any) -> Any:
        return None

    def extern(self, *args: Any, **kwargs: Any) -> Any:
        return None

    def check(self, *args: Any, **kwargs: Any) -> None:
        pass

    def compile(self, *args: Any, **kwargs: Any) -> Any:
        return None

    def compile_function(self, *args: Any, **kwargs: Any) -> Any:
        return None

    def pytket(self, *args: Any, **kwargs: Any) -> Any:
        return lambda f: f

    def load_pytket(self, *args: Any, **kwargs: Any) -> Any:
        return None


def _dummy_custom_decorator(*args: Any, **kwargs: Any) -> Any:
    """Dummy version of custom decorators that are used during Sphinx builds."""
    return lambda f: f


def sphinx_running() -> bool:
    """Checks if guppylang was imported during a sphinx build."""
    # This is the most general solution available at the moment.
    # See: https://github.com/sphinx-doc/sphinx/issues/9805
    try:
        import sphinx  # type: ignore[import-untyped, import-not-found, unused-ignore]

        return hasattr(sphinx, "application")
    except ImportError:
        return False
