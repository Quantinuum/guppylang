from typing import Any

from guppylang.decorator import Effect


class Effects:
    """Dummy class to support `@effects` annotations."""

    effects: list[Effect]

    def __init__(self, *effects: Effect) -> None:
        self.effects = list(effects)

    def __rmatmul__(self, other: Any) -> Any:
        # This method is to make the Python interpreter happy with @comptime at runtime
        return other


effects = Effects

ANY = Effect.ANY
