from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
Out = TypeVar("Out")


def produce_moved_function(
    module: str, old_name: str, new_location: str
) -> Callable[P, Out]:
    def moved_function(*_args: P.args, **_kwargs: P.kwargs) -> Out:
        raise ImportError(
            f"The function `{old_name}` has been moved to `{new_location}`, and "
            f"can no longer be imported from `{module}`."
        )

    return moved_function
