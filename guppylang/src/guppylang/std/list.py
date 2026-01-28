"""EXPERIMENTAL: The `list` type"""

# ruff: noqa: E501
# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def, type-arg"

from __future__ import annotations

from typing import TYPE_CHECKING, Generic

from guppylang_internals.decorator import custom_function, extend_type, hugr_op
from guppylang_internals.definition.custom import NoopCompiler
from guppylang_internals.std._internal.checker import UnsupportedChecker
from guppylang_internals.std._internal.compiler.list import (
    ListGetitemCompiler,
    ListLengthCompiler,
    ListPopCompiler,
    ListPushCompiler,
    ListSetitemCompiler,
)
from guppylang_internals.std._internal.util import unsupported_op
from guppylang_internals.tys.builtin import list_type_def

from guppylang import guppy
from guppylang.std.option import Option  # noqa: TC001

if TYPE_CHECKING:
    from guppylang.std.lang import owned


T = guppy.type_var("T")
L = guppy.type_var("L", copyable=False, droppable=False)


@extend_type(list_type_def)
class list(Generic[T]):
    """Mutable sequence items with homogeneous types."""

    @custom_function(ListGetitemCompiler())
    def __getitem__(self: list[L], idx: int) -> L: ...

    @custom_function(ListSetitemCompiler())
    def __setitem__(self: list[L], idx: int, value: L @ owned) -> None: ...

    @custom_function(ListLengthCompiler())
    def __len__(self: list[L]) -> int: ...

    @custom_function(checker=UnsupportedChecker(), higher_order_value=False)
    def __new__(x): ...

    @custom_function(NoopCompiler())  # TODO: define via Guppy source instead
    def __iter__(self: list[L] @ owned) -> list[L]: ...

    @hugr_op(unsupported_op("pop"))
    def __next__(self: list[L] @ owned) -> Option[tuple[L, list[L]]]: ...

    @custom_function(ListPushCompiler())
    def append(self: list[L], item: L @ owned) -> None: ...

    @custom_function(ListPopCompiler())
    def pop(self: list[L]) -> L: ...
