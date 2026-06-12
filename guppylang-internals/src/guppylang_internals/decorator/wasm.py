from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING, ParamSpec, TypeVar, overload

from guppylang.defs import GuppyFunctionDefinition

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
from guppylang_internals.std._internal.decorator import (
    ext_module_decorator,
)
from guppylang_internals.std._internal.wasm import (
    WasmFileNotFound,
    WasmFunctionNotInFile,
    WasmPlatform,
    WasmSignatureError,
    decode_wasm_functions,
)
from guppylang_internals.tys.builtin import WasmModuleTypeDef
from guppylang_internals.tys.ty import FunctionType

if TYPE_CHECKING:
    import ast
    import builtins
    from collections.abc import Callable

    from guppylang.defs import GuppyDefinition

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
        def_id: DefId,
        name: str,
        defined_at: ast.AST | None,
        filename: str,
        config_filename: str | None,
    ) -> OpaqueTypeDef:
        assert config_filename is None
        return WasmModuleTypeDef(def_id, name, defined_at, filename, wasm_platform)

    def check_member(val: GuppyDefinition) -> None:
        wasm_def: RawWasmFunctionDef
        if isinstance(val, GuppyFunctionDefinition) and isinstance(
            val.wrapped, RawWasmFunctionDef
        ):
            wasm_def = val.wrapped
        else:
            return None
        # wasm_sigs should only have not been provided if we have
        # defined @wasm functions in a class which didn't use the
        # @wasm_module decorator.
        assert wasm_sigs is not None
        if wasm_def.wasm_index is not None:
            name = wasm_sigs.functions[wasm_def.wasm_index]
            assert name in wasm_sigs.function_sigs
            wasm_sig_or_err = wasm_sigs.function_sigs[name]
        else:
            if wasm_def.name in wasm_sigs.function_sigs:
                wasm_sig_or_err = wasm_sigs.function_sigs[wasm_def.name]
            else:
                raise GuppyError(
                    WasmFunctionNotInFile(
                        wasm_def.defined_at,
                        wasm_def.name,
                    ).add_sub_diagnostic(
                        WasmFunctionNotInFile.WasmFileNote(
                            None,
                            wasm_sigs.filename,
                        )
                    )
                )
        if isinstance(wasm_sig_or_err, FunctionType):
            DEF_STORE.register_wasm_function(wasm_def.id, wasm_sig_or_err)
        elif isinstance(wasm_sig_or_err, str):
            raise GuppyError(
                WasmSignatureError(
                    None, wasm_def.name, filename, wasm_platform.value
                ).add_sub_diagnostic(WasmSignatureError.Message(None, wasm_sig_or_err))
            )

    create_decorator = ext_module_decorator(  # type: ignore[var-annotated]
        type_def_wrapper,
        WasmModuleInitCompiler(),
        WasmModuleDiscardCompiler(),
        init_arg=True,
        foreach_member=check_member,
    )
    return create_decorator(str(wasm_path), config_filename=None)


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
