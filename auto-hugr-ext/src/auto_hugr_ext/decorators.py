"""`@ext_type` / `@ext_op` decorators for declaring a new HUGR extension."""

from __future__ import annotations

import ast
import inspect
import textwrap
from typing import TYPE_CHECKING, Any, overload

from guppylang_internals.checker.core import Globals
from guppylang_internals.decorator import custom_type, hugr_op
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.tys.parsing import parse_parameter
from hugr import tys as ht

from auto_hugr_ext.state import EXTENSION_STATE

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from types import FrameType

    from guppylang.defs import GuppyFunctionDefinition
    from guppylang_internals.compiler.core import CompilerContext
    from guppylang_internals.tys.arg import Argument
    from guppylang_internals.tys.common import ToHugrContext
    from guppylang_internals.tys.param import Parameter
    from guppylang_internals.tys.subst import Inst

__all__ = ["ext_op", "ext_type"]


def _caller_frame(depth: int) -> FrameType:
    """The frame `depth` levels above the caller of this function."""
    frame = inspect.currentframe()
    for _ in range(depth + 1):
        assert frame is not None
        frame = frame.f_back
    assert frame is not None
    return frame


def _params_from_class(cls: type, frame: FrameType) -> list[Parameter]:
    """Parses class parameters."""
    source_lines, _ = inspect.getsourcelines(cls)
    module = ast.parse(textwrap.dedent("".join(source_lines)))
    class_node = next(node for node in module.body if isinstance(node, ast.ClassDef))
    globals = Globals(frame)
    params: list[Parameter] = []
    mapping: dict[str, Parameter] = {}
    for idx, node in enumerate(class_node.type_params):
        param = parse_parameter(node, idx, globals, mapping)
        params.append(param)
        mapping[param.name] = param
    return params


def ext_type[T](
    copyable: bool = True,
    droppable: bool = True,
    name: str | None = None,
    params: Sequence[Parameter] | None = None,
) -> Callable[[type[T]], type[T]]:
    """Declares a class as an opaque type of the extension being generated."""
    frame = _caller_frame(1)

    def dec(cls: type[T]) -> type[T]:
        ty_name = name or cls.__name__
        ty_params = (
            list(params) if params is not None else _params_from_class(cls, frame)
        )
        bound = ht.TypeBound.Copyable if copyable and droppable else ht.TypeBound.Linear

        def to_hugr(args: Sequence[Argument], ctx: ToHugrContext) -> ht.Type:
            extension = EXTENSION_STATE.extension
            if extension is None:
                raise RuntimeError(
                    "Generate the HUGR extension before lowering its types"
                )
            return extension.get_type(ty_name).instantiate(
                [arg.to_hugr(ctx) for arg in args]
            )

        defn = custom_type(
            to_hugr,
            name=ty_name,
            copyable=copyable,
            droppable=droppable,
            bound=bound,
            params=ty_params,
        )(cls)
        opaque_def = defn.wrapped  # type: ignore[attr-defined]
        # `custom_type` records its own caller, which is this module.
        DEF_STORE.frames[opaque_def.id] = frame
        return defn

    return dec


@overload
def ext_op[**P, T](func: Callable[P, T], /) -> GuppyFunctionDefinition[P, T]: ...


@overload
def ext_op[**P, T](
    *, override_name: str | None = None
) -> Callable[[Callable[P, T]], GuppyFunctionDefinition[P, T]]: ...


def ext_op(func: Any = None, /, *, override_name: str | None = None) -> Any:
    """Declares a function as an operation of the extension being generated."""
    # Captured here rather than in `dec` since only this function is guaranteed to be
    # called directly from the declaring scope.
    frame = _caller_frame(1)

    def dec(f: Any) -> Any:
        py_name = f.__func__.__name__ if isinstance(f, staticmethod) else f.__name__
        op_name = override_name or py_name

        def make_op(ty: ht.FunctionType, inst: Inst, ctx: CompilerContext) -> Any:
            extension = EXTENSION_STATE.extension
            if extension is None:
                raise RuntimeError(
                    "Generate the HUGR extension before compiling its ops"
                )
            return extension.get_op(op_name).instantiate(
                args=[arg.to_hugr(ctx) for arg in inst], concrete_signature=ty
            )

        defn = hugr_op(make_op, name=op_name)(f)
        # `custom_function` records its own caller, which is this module.
        DEF_STORE.frames[defn.id] = frame
        return defn

    return dec if func is None else dec(func)
