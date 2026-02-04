from typing import Any

from typing_extensions import Self

from guppylang_internals.error import GuppyComptimeError

ERROR_MSG = (
    "This list is an owned function argument. Therefore, this mutation won't be "
    "visible to the caller. Consider calling `copy()` to obtain a mutable local copy "
    "of this list."
)


class frozenlist(list):  # type: ignore[type-arg]
    """An immutable list subclass.

    Raises a `GuppyComptimeError` for any operation that would mutate the list.
    """

    def append(self, *args: Any, **kwargs: Any) -> None:
        raise GuppyComptimeError(ERROR_MSG)

    def copy(self) -> Any:
        return list(self)

    def clear(self, *args: Any, **kwargs: Any) -> None:
        raise GuppyComptimeError(ERROR_MSG)

    def extend(self, *args: Any, **kwargs: Any) -> None:
        raise GuppyComptimeError(ERROR_MSG)

    def insert(self, *args: Any, **kwargs: Any) -> None:
        raise GuppyComptimeError(ERROR_MSG)

    def pop(self, *args: Any, **kwargs: Any) -> Any:
        raise GuppyComptimeError(ERROR_MSG)

    def remove(self, *args: Any, **kwargs: Any) -> None:
        raise GuppyComptimeError(ERROR_MSG)

    def reverse(self, *args: Any, **kwargs: Any) -> None:
        raise GuppyComptimeError(ERROR_MSG)

    def sort(self, *args: Any, **kwargs: Any) -> None:
        raise GuppyComptimeError(ERROR_MSG)

    def __delitem__(self, *args: Any, **kwargs: Any) -> None:
        raise GuppyComptimeError(ERROR_MSG)

    def __iadd__(self, *args: Any, **kwargs: Any) -> Self:  # type: ignore[misc]
        raise GuppyComptimeError(ERROR_MSG)

    def __imul__(self, *args: Any, **kwargs: Any) -> Self:  # type: ignore[misc]
        raise GuppyComptimeError(ERROR_MSG)

    def __setitem__(self, key: Any, value: Any) -> Any:
        raise GuppyComptimeError(ERROR_MSG)
