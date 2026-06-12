from __future__ import annotations

from typing import TYPE_CHECKING, ParamSpec, TypeVar, overload

from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.custom import DefaultCallChecker
from guppylang_internals.definition.gpu import GpuModuleTypeDef, RawGpuFunctionDef
from guppylang_internals.dummy_decorator import _dummy_custom_decorator, sphinx_running
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.frame_util import get_calling_frame
from guppylang_internals.std._internal.compiler.gpu import (
    GpuModuleCallCompiler,
    GpuModuleDiscardCompiler,
    GpuModuleInitCompiler,
)
from guppylang_internals.std._internal.decorator import ext_module_decorator

if TYPE_CHECKING:
    import ast
    import builtins
    from collections.abc import Callable

    from guppylang.defs import GuppyDefinition, GuppyFunctionDefinition

    from guppylang_internals.definition.ty import OpaqueTypeDef

T = TypeVar("T")
P = ParamSpec("P")


def gpu_module(
    filename: str, config_filename: str | None
) -> Callable[[builtins.type[T]], GuppyDefinition]:
    def type_def_wrapper(
        def_id: DefId,
        name: str,
        defined_at: ast.AST | None,
        filename: str,
        config_filename: str | None,
    ) -> OpaqueTypeDef:
        return GpuModuleTypeDef(def_id, name, defined_at, filename, config_filename)

    create_decorator = ext_module_decorator(  # type: ignore[var-annotated]
        type_def_wrapper,
        GpuModuleInitCompiler(),
        GpuModuleDiscardCompiler(),
        init_arg=False,
    )
    return create_decorator(filename, config_filename)


@overload
def gpu(arg: Callable[P, T]) -> GuppyFunctionDefinition[P, T]: ...
@overload
def gpu(arg: int) -> Callable[[Callable[P, T]], GuppyFunctionDefinition[P, T]]: ...
def gpu(
    arg: int | Callable[P, T],
) -> (
    GuppyFunctionDefinition[P, T]
    | Callable[[Callable[P, T]], GuppyFunctionDefinition[P, T]]
):
    if isinstance(arg, int):

        def wrapper(f: Callable[P, T]) -> GuppyFunctionDefinition[P, T]:
            return _gpu_helper(arg, f)

        return wrapper
    else:
        return _gpu_helper(None, arg)


def _gpu_helper(fn_id: int | None, f: Callable[P, T]) -> GuppyFunctionDefinition[P, T]:
    from guppylang.defs import GuppyFunctionDefinition

    func = RawGpuFunctionDef(
        DefId.fresh(),
        f.__name__,
        None,
        f,
        DefaultCallChecker(),
        GpuModuleCallCompiler(f.__name__, fn_id),
        True,
        signature=None,
    )
    DEF_STORE.register_def(func, get_calling_frame())
    return GuppyFunctionDefinition(func)


# Override decorators with dummy versions if we're running a sphinx build
if not TYPE_CHECKING and sphinx_running():
    custom_function = _dummy_custom_decorator
    hugr_op = _dummy_custom_decorator
    extend_type = _dummy_custom_decorator
    custom_type = _dummy_custom_decorator
    gpu_module = _dummy_custom_decorator
    gpu = _dummy_custom_decorator()
