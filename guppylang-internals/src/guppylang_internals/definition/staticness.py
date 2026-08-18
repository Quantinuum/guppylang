from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from guppylang_internals.definition.common import Definition
from guppylang_internals.diagnostic import Error
from guppylang_internals.error import GuppyError, InternalGuppyError

PyFunc = Callable[..., Any]


@dataclass(frozen=True)
class OverloadInvalidStaticError(Error):
    title: ClassVar[str] = "Invalid static overloads"
    func: str
    static_overloads: list[str]
    non_static_overloads: list[str]

    @property
    def rendered_span_label(self) -> str:
        stem = f"""Some overloads of method `{self.func}` are static but others are not
        static: {", ".join(f"`{n}`" for n in self.static_overloads)}
        non-static: {", ".join(f"`{n}`" for n in self.non_static_overloads)}"""
        return stem


def determine_static(defn: Definition) -> tuple[bool, PyFunc | None]:
    """Check if a Definition corresponds to a static method.

    Also returns the wrapped method if applicable.
    """
    from guppylang_internals.definition.custom import RawCustomFunctionDef
    from guppylang_internals.definition.declaration import RawFunctionDecl
    from guppylang_internals.definition.function import RawFunctionDef
    from guppylang_internals.definition.overloaded import OverloadedFunctionDef
    from guppylang_internals.definition.pytket_circuits import (
        RawLoadPytketDef,
        RawPytketDef,
    )
    from guppylang_internals.definition.traced import RawTracedFunctionDef
    from guppylang_internals.engine import DEF_STORE

    match defn:
        case (
            RawFunctionDef()
            | RawCustomFunctionDef()
            | RawFunctionDecl()
            | RawTracedFunctionDef()
        ):
            if isinstance(defn.python_func, staticmethod):
                return True, defn.python_func.__func__
            else:
                return False, None
        case OverloadedFunctionDef():
            # check all the methods in the overload are also static and error if not
            # returns None regardless of staticness as there is nothing to unwrap
            func_defs = [DEF_STORE.raw_defs[func_id] for func_id in defn.func_ids]
            is_static = [determine_static(func_def)[0] for func_def in func_defs]
            if all(is_static):
                return True, None
            elif not any(is_static):
                return False, None
            else:
                static_func_names = [
                    func_defs[i].name for i, static in enumerate(is_static) if static
                ]
                non_static_func_names = [
                    func_defs[i].name
                    for i, static in enumerate(is_static)
                    if not static
                ]
                raise GuppyError(
                    OverloadInvalidStaticError(
                        defn.defined_at,
                        defn.name,
                        static_func_names,
                        non_static_func_names,
                    )
                )
        case RawPytketDef() | RawLoadPytketDef():
            return False, None
        case _:
            raise InternalGuppyError(
                f"Cannot determine staticness of Definition of type {type(defn)}"
            )
