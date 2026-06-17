from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING, ParamSpec, TypeVar, overload

from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.wasm import RawWasmFunctionDef
from guppylang_internals.dummy_decorator import _dummy_custom_decorator, sphinx_running
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.error import GuppyError, pretty_errors
from guppylang_internals.frame_util import get_calling_frame
from guppylang_internals.std._internal.checker import WasmCallChecker
from guppylang_internals.std._internal.compiler.wasm import (
    WasmModuleCallCompiler,
    WasmModuleDiscardCompiler,
    WasmModuleInitCompiler,
)
from guppylang_internals.std._internal.decorator import ext_module_decorator
from guppylang_internals.std._internal.wasm import (
    WasmFileNotFound,
    WasmPlatform,
    decode_wasm_functions,
)
from guppylang_internals.tys.builtin import WasmModuleTypeDef

if TYPE_CHECKING:
    import ast
    import builtins
    from collections.abc import Callable

    from guppylang.defs import GuppyDefinition, GuppyFunctionDefinition

    from guppylang_internals.definition.ty import OpaqueTypeDef

T = TypeVar("T")
P = ParamSpec("P")


@pretty_errors
def wasm_module(
    filename: str,
    wasm_platform: WasmPlatform = WasmPlatform.Helios,
) -> Callable[[builtins.type[T]], GuppyDefinition]:
    wasm_path = pathlib.Path(filename)
    # Absolute paths are used as-is; relative paths are resolved against the
    # caller's source file directory (not the current working directory).
    if not wasm_path.is_absolute():
        frame = get_calling_frame()
        if (caller_file := frame.f_globals.get("__file__")) is not None:
            caller_dir = pathlib.Path(caller_file).resolve().parent
            wasm_path = caller_dir / filename

    if wasm_path.is_file():
        wasm_sigs = decode_wasm_functions(str(wasm_path), wasm_platform)
    else:
        raise GuppyError(WasmFileNotFound(None, filename))

    def type_def_wrapper(
        id: DefId,
        name: str,
        defined_at: ast.AST | None,
        wasm_file: str,
        wasm_plat: WasmPlatform,
        config: str | None,
    ) -> OpaqueTypeDef:
        assert config is None
        return WasmModuleTypeDef(id, name, defined_at, wasm_file, wasm_plat)

    decorator = ext_module_decorator(
        type_def_wrapper,
        WasmModuleInitCompiler(),
        WasmModuleDiscardCompiler(),
        True,
        wasm_sigs,
    )

    def inner_fun(ty: builtins.type[T]) -> GuppyDefinition:
        decorator_inner = decorator(str(wasm_path), wasm_platform, None)
        return decorator_inner(ty)

    return inner_fun


@overload
def wasm(arg: Callable[P, T]) -> GuppyFunctionDefinition[P, T]: ...
@overload
def wasm(arg: int) -> Callable[[Callable[P, T]], GuppyFunctionDefinition[P, T]]: ...
def wasm(
    arg: int | Callable[P, T],
) -> (
    GuppyFunctionDefinition[P, T]
    | Callable[[Callable[P, T]], GuppyFunctionDefinition[P, T]]
):
    if isinstance(arg, int):

        def wrapper(f: Callable[P, T]) -> GuppyFunctionDefinition[P, T]:
            return _wasm_helper(arg, f)

        return wrapper
    else:
        return _wasm_helper(None, arg)


def _wasm_helper(fn_id: int | None, f: Callable[P, T]) -> GuppyFunctionDefinition[P, T]:
    from guppylang.defs import GuppyFunctionDefinition

    func = RawWasmFunctionDef(
        DefId.fresh(),
        f.__name__,
        None,
        f,
        WasmCallChecker(),
        WasmModuleCallCompiler(f.__name__, fn_id),
        True,
        signature=None,
        wasm_index=fn_id,
    )
    DEF_STORE.register_def(func, get_calling_frame())
    return GuppyFunctionDefinition(func)


# Override decorators with dummy versions if we're running a sphinx build
if not TYPE_CHECKING and sphinx_running():
    wasm_module = _dummy_custom_decorator()
    wasm = _dummy_custom_decorator()
