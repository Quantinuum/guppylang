from collections.abc import Callable
from typing import Any, ParamSpec, Self, TypeVar

P = ParamSpec("P")
Out = TypeVar("Out")


def produce_moved_function(
    module: str, old_name: str, new_location: str
) -> Callable[P, Out]:
    """Produces a function that raises an import error when used, stating that it
    cannot be used any more from the current location. This is a temporary migration
    mechanism, and should be considered for removal several months after the move."""

    def moved_function(*_args: P.args, **_kwargs: P.kwargs) -> Out:
        raise ImportError(
            f"The function `{old_name}` has been moved to `{new_location}`, and "
            f"can no longer be imported from `{module}`."
        )

    return moved_function


def produce_moved_class(module: str, old_name: str, new_location: str) -> type:
    """Produces a class that raises an import error when instantiated, stating that it
    cannot be used any more from the current location. This is a temporary migration
    mechanism, and should be considered for removal several months after the move."""

    class MovedClass:
        def __new__(cls, *_args: P.args, **_kwargs: P.kwargs) -> Self:  # type: ignore[valid-type]
            raise ImportError(
                f"The class `{old_name}` has been moved to `{new_location}`, and "
                f"can no longer be imported from `{module}`."
            )

        def __class_getitem__(cls, item: Any) -> type:
            # Gracefully handles subscripting of the type in positions that are
            # evaluated by the Python interpreter
            raise ImportError(
                f"The class `{old_name}` has been moved to `{new_location}`, and "
                f"can no longer be imported from `{module}`."
            )

    return MovedClass
