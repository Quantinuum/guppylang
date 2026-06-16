from __future__ import annotations

from typing import TYPE_CHECKING, ParamSpec, TypeVar

from guppylang_internals.dummy_decorator import _dummy_custom_decorator, sphinx_running
from guppylang_internals.engine import DEF_STORE

if TYPE_CHECKING:
    from collections.abc import Callable

    from guppylang_internals.definition.ty import TypeDef

T = TypeVar("T")
P = ParamSpec("P")


def extend_type(defn: TypeDef, return_class: bool = False) -> Callable[[type], type]:
    """Decorator to add new instance functions to a type.

    By default, returns a `GuppyDefinition` object referring to the type. Alternatively,
    `return_class=True` can be set to return the decorated class unchanged.
    """
    from guppylang.defs import GuppyDefinition

    def dec(c: type) -> type:
        for val in c.__dict__.values():
            if isinstance(val, GuppyDefinition):
                DEF_STORE.register_type_member(defn.id, val.wrapped.name, val.id)
        return c if return_class else GuppyDefinition(defn)  # type: ignore[return-value]

    return dec


# Override decorators with dummy versions if we're running a sphinx build
if not TYPE_CHECKING and sphinx_running():
    extend_type = _dummy_custom_decorator
