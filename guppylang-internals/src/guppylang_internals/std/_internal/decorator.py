import ast
import builtins
from collections.abc import Callable
from typing import TypeVar

from guppylang.defs import GuppyDefinition, GuppyFunctionDefinition

from guppylang_internals.compiler.core import (
    GlobalConstId,
)
from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.custom import (
    CustomFunctionDef,
    CustomInoutCallCompiler,
    DefaultCallChecker,
)
from guppylang_internals.definition.ty import OpaqueTypeDef
from guppylang_internals.definition.wasm import RawWasmFunctionDef
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.error import GuppyError, pretty_errors
from guppylang_internals.frame_util import get_calling_frame
from guppylang_internals.std._internal.wasm import (
    ConcreteWasmModule,
    WasmFunctionNotInFile,
    WasmPlatform,
    WasmSignatureError,
)
from guppylang_internals.tys import Effect
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
)

T = TypeVar("T")


def ext_module_decorator(
    type_def: Callable[
        [DefId, str, ast.AST | None, str, WasmPlatform, str | None], OpaqueTypeDef
    ],
    init_compiler: CustomInoutCallCompiler,
    discard_compiler: CustomInoutCallCompiler,
    init_arg: bool,  # Whether the init function should take a nat argument
    wasm_sigs: ConcreteWasmModule
    | None = None,  # For @wasm_module, we must be passed a parsed wasm file
) -> Callable[
    [str, WasmPlatform, str | None], Callable[[builtins.type[T]], GuppyDefinition]
]:
    def fun(
        filename: str, wasm_plat: WasmPlatform, module: str | None
    ) -> Callable[[builtins.type[T]], GuppyDefinition]:
        @pretty_errors
        def dec(cls: builtins.type[T]) -> GuppyDefinition:
            # N.B. Only one module per file and vice-versa
            ext_module = type_def(
                DefId.fresh(),
                cls.__name__,
                None,
                filename,
                wasm_plat,
                module,
            )

            ext_module_ty = ext_module.check_instantiate([], None)

            DEF_STORE.register_def(ext_module, get_calling_frame())
            for val in cls.__dict__.values():
                if isinstance(val, GuppyDefinition):
                    DEF_STORE.register_type_member(
                        ext_module.id, val.wrapped.name, val.id
                    )
                    wasm_def: RawWasmFunctionDef
                    if isinstance(val, GuppyFunctionDefinition) and isinstance(
                        val.wrapped, RawWasmFunctionDef
                    ):
                        wasm_def = val.wrapped
                    else:
                        continue
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
                                None, wasm_def.name, filename, wasm_plat.value
                            ).add_sub_diagnostic(
                                WasmSignatureError.Message(None, wasm_sig_or_err)
                            )
                        )

            # Add a constructor to the class
            if init_arg:
                init_fn_ty = FunctionType(
                    [
                        FuncInput(
                            NumericType(NumericType.Kind.Nat),
                            flags=InputFlags.Owned,
                        )
                    ],
                    ext_module_ty,
                )
            else:
                init_fn_ty = FunctionType([], ext_module_ty)

            call_method = CustomFunctionDef(
                DefId.fresh(),
                "__new__",
                None,
                init_fn_ty,
                DefaultCallChecker(),
                init_compiler,
                True,
                GlobalConstId.fresh(f"{cls.__name__}.__new__"),
                effects=[Effect.ANY],  # ALAN does DefaultCallChecker even use this?
                has_signature=True,
                has_var_args=False,
            )
            discard = CustomFunctionDef(
                DefId.fresh(),
                "discard",
                None,
                FunctionType([FuncInput(ext_module_ty, InputFlags.Owned)], NoneType()),
                DefaultCallChecker(),
                discard_compiler,
                False,
                GlobalConstId.fresh(f"{cls.__name__}.__discard__"),
                effects=[Effect.ANY],  # ALAN does DefaultCallChecker even use this?
                has_signature=True,
                has_var_args=False,
            )
            DEF_STORE.register_def(call_method, get_calling_frame())
            DEF_STORE.register_type_member(ext_module.id, "__new__", call_method.id)
            DEF_STORE.register_def(discard, get_calling_frame())
            DEF_STORE.register_type_member(ext_module.id, "discard", discard.id)

            return GuppyDefinition(ext_module)

        return dec

    return fun
