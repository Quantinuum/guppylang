from __future__ import annotations

from typing import TYPE_CHECKING, ParamSpec, TypeVar

from guppylang_internals.dummy_decorator import _dummy_custom_decorator, sphinx_running
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.error import InternalGuppyError

if TYPE_CHECKING:
    from collections.abc import Callable

    from guppylang_internals.definition.common import Definition
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


def determine_static(defn: Definition) -> bool:
    """Check if a Definition corresponds to a static method."""
    from guppylang_internals.definition.custom import RawCustomFunctionDef
    from guppylang_internals.definition.declaration import RawFunctionDecl
    from guppylang_internals.definition.function import RawFunctionDef
    from guppylang_internals.definition.overloaded import OverloadedFunctionDef
    from guppylang_internals.definition.traced import RawTracedFunctionDef
    from guppylang_internals.engine import DEF_STORE

    match defn:
        case RawFunctionDef() | RawCustomFunctionDef() | RawFunctionDecl():
            return isinstance(defn.python_func, staticmethod)
        # comptime methods not yet supported
        case RawTracedFunctionDef():
            if isinstance(defn.python_func, staticmethod):
                raise TypeError(
                    f"Unsupported: static method `{defn.name}`\
                    comptime static methods not supported"
                )
            else:
                return False
        case OverloadedFunctionDef():
            # check all the methods in the overload are also static
            num_overloads = len(defn.func_ids)
            func_defs = [DEF_STORE.raw_defs[func_id] for func_id in defn.func_ids]
            is_static = [determine_static(func_def) for func_def in func_defs]
            if all(is_static):
                return True
            elif not any(is_static):
                return False
            else:
                static_indices = [i for i, static in enumerate(is_static) if static]
                non_static_indices = [
                    i for i in range(num_overloads) if i not in static_indices
                ]
                raise TypeError(
                    f"Some implementations of overloaded method are static whereas "
                    "others are not "
                    f"static: {[func_defs[i].name for i in static_indices]} "
                    f"non-static: {[func_defs[i].name for i in non_static_indices]}"
                )
        case _:
            raise InternalGuppyError(
                f"Cannot determine staticness of Definition of type \
                {type(defn)}"
            )


# Override decorators with dummy versions if we're running a sphinx build
if not TYPE_CHECKING and sphinx_running():
    extend_type = _dummy_custom_decorator
