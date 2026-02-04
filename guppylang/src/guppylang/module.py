from typing import Any


class GuppyModule:
    """A Guppy module that may contain function and type definitions."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        err = (
            "Explicit Guppy modules are no longer supported. Use the regular `@guppy` "
            "decorator without passing a module and use `foo.compile()` to "
            "compile Guppy functions."
        )
        raise RuntimeError(err)
