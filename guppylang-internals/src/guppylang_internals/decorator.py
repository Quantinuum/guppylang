from __future__ import annotations

import inspect
import pathlib
from typing import TYPE_CHECKING, ParamSpec, TypeVar, overload

from guppylang.defs import GuppyDefinition, GuppyFunctionDefinition
from hugr import ops
from hugr import tys as ht

from guppylang_internals.compiler.core import (
    CompilerContext,
    GlobalConstId,
)
from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.custom import (
    CustomCallChecker,
    CustomFunctionDef,
    CustomInoutCallCompiler,
    DefaultCallChecker,
    NotImplementedCallCompiler,
    OpCompiler,
    RawCustomFunctionDef,
)
from guppylang_internals.definition.ty import OpaqueTypeDef, TypeDef
from guppylang_internals.definition.wasm import RawWasmFunctionDef
from guppylang_internals.dummy_decorator import _dummy_custom_decorator, sphinx_running
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.error import GuppyError, pretty_errors
from guppylang_internals.std._internal.checker import WasmCallChecker
from guppylang_internals.std._internal.compiler.wasm import (
    WasmModuleCallCompiler,
    WasmModuleDiscardCompiler,
    WasmModuleInitCompiler,
)
from guppylang_internals.tys.builtin import (
    WasmModuleTypeDef,
)
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
    UnitaryFlags,
)
from guppylang_internals.wasm_util import (
    ConcreteWasmModule,
    WasmFileNotFound,
    WasmFunctionNotInFile,
    WasmSignatureError,
    decode_wasm_functions,
)

if TYPE_CHECKING:
    import ast
    import builtins
    from collections.abc import Callable, Sequence
    from types import FrameType

    from guppylang_internals.tys.arg import Argument
    from guppylang_internals.tys.param import Parameter
    from guppylang_internals.tys.subst import Inst

T = TypeVar("T")
P = ParamSpec("P")


def get_calling_frame() -> FrameType:
    """Finds the first frame that called this function outside the compiler modules."""
    frame = inspect.currentframe()
    while frame:
        module = inspect.getmodule(frame)
        if module is None:
            return frame
        if module.__file__ != __file__:
            return frame
        frame = frame.f_back
    raise RuntimeError("Couldn't obtain stack frame for definition")


def custom_function(
    compiler: CustomInoutCallCompiler | None = None,
    checker: CustomCallChecker | None = None,
    higher_order_value: bool = True,
    name: str = "",
    signature: FunctionType | None = None,
    unitary_flags: UnitaryFlags = UnitaryFlags.NoFlags,
    has_var_args: bool = False,
) -> Callable[[Callable[P, T]], GuppyFunctionDefinition[P, T]]:
    """Decorator to add custom typing or compilation behaviour to function decls.

    Optionally, usage of the function as a higher-order value can be disabled. In
    that case, the function signature can be omitted if a custom call compiler is
    provided.
    """
    from guppylang.defs import GuppyFunctionDefinition

    def dec(f: Callable[P, T]) -> GuppyFunctionDefinition[P, T]:
        call_checker = checker or DefaultCallChecker()
        if signature is not None:
            object.__setattr__(signature, "unitary_flags", unitary_flags)
        func = RawCustomFunctionDef(
            DefId.fresh(),
            name or f.__name__,
            None,
            f,
            call_checker,
            compiler or NotImplementedCallCompiler(),
            higher_order_value,
            signature,
            unitary_flags,
            has_var_args,
        )
        DEF_STORE.register_def(func, get_calling_frame())
        return GuppyFunctionDefinition(func)

    return dec


def hugr_op(
    op: Callable[[ht.FunctionType, Inst, CompilerContext], ops.DataflowOp],
    checker: CustomCallChecker | None = None,
    higher_order_value: bool = True,
    name: str = "",
    signature: FunctionType | None = None,
    unitary_flags: UnitaryFlags = UnitaryFlags.NoFlags,
) -> Callable[[Callable[P, T]], GuppyFunctionDefinition[P, T]]:
    """Decorator to annotate function declarations as HUGR ops.

    Args:
        op: A function that takes an instantiation of the type arguments as well as
            the inferred input and output types and returns a concrete HUGR op.
        checker: The custom call checker.
        higher_order_value: Whether the function may be used as a higher-order
            value.
        name: The name of the function.
    """
    return custom_function(
        OpCompiler(op),
        checker,
        higher_order_value,
        name,
        signature,
        unitary_flags=unitary_flags,
    )


def extend_type(defn: TypeDef, return_class: bool = False) -> Callable[[type], type]:
    """Decorator to add new instance functions to a type.

    By default, returns a `GuppyDefinition` object referring to the type. Alternatively,
    `return_class=True` can be set to return the decorated class unchanged.
    """
    from guppylang.defs import GuppyDefinition

    def dec(c: type) -> type:
        for val in c.__dict__.values():
            if isinstance(val, GuppyDefinition):
                DEF_STORE.register_impl(defn.id, val.wrapped.name, val.id)
        return c if return_class else GuppyDefinition(defn)  # type: ignore[return-value]

    return dec


def custom_type(
    hugr_ty: ht.Type | Callable[[Sequence[Argument], CompilerContext], ht.Type],
    name: str = "",
    copyable: bool = True,
    droppable: bool = True,
    bound: ht.TypeBound | None = None,
    params: Sequence[Parameter] | None = None,
) -> Callable[[type[T]], type[T]]:
    """Decorator to annotate a class definitions as Guppy types.

    Requires the static Hugr translation of the type. Additionally, the type can be
    marked as linear. All `@guppy` annotated functions on the class are turned into
    instance functions.

    For non-generic types, the Hugr representation can be passed as a static value.
    For generic types, a callable may be passed that takes the type arguments of a
    concrete instantiation.
    """
    from guppylang.defs import GuppyDefinition

    mk_hugr_ty = (
        (lambda args, ctx: hugr_ty) if isinstance(hugr_ty, ht.Type) else hugr_ty
    )

    def dec(c: type[T]) -> type[T]:
        defn = OpaqueTypeDef(
            DefId.fresh(),
            name or c.__name__,
            None,
            params or [],
            not copyable,
            not droppable,
            mk_hugr_ty,  # type: ignore[arg-type]
            bound,
        )
        DEF_STORE.register_def(defn, get_calling_frame())
        for val in c.__dict__.values():
            if isinstance(val, GuppyDefinition):
                DEF_STORE.register_impl(defn.id, val.wrapped.name, val.id)
        # We're pretending to return the class unchanged, but in fact we return
        # a `GuppyDefinition` that handles the comptime logic
        return GuppyDefinition(defn)  # type: ignore[return-value]

    return dec


@pretty_errors
def wasm_module(
    filename: str,
) -> Callable[[builtins.type[T]], GuppyDefinition]:
    wasm_path = pathlib.Path(filename)

    # Absolute paths are used as-is; relative paths are resolved against the
    # caller's source file directory (not the current working directory).
    if not wasm_path.is_absolute():
        # Walk up the call stack past guppylang-internal frames to find the
        # user's source file.  We skip frames whose module name starts with
        # "guppylang" so that the decorator works regardless of how deeply it
        # is called from within the library.
        caller_file = None
        frame = inspect.currentframe()
        while frame:
            module = inspect.getmodule(frame)
            if module is None or not module.__name__.startswith("guppylang"):
                caller_file = frame.f_globals.get("__file__")
                break
            frame = frame.f_back
        if caller_file is not None:
            caller_dir = pathlib.Path(caller_file).resolve().parent
            wasm_path = caller_dir / filename

    if wasm_path.is_file():
        wasm_sigs = decode_wasm_functions(str(wasm_path))
    else:
        raise GuppyError(WasmFileNotFound(None, filename))

    def type_def_wrapper(
        id: DefId,
        name: str,
        defined_at: ast.AST | None,
        wasm_file: str,
        config: str | None,
    ) -> OpaqueTypeDef:
        assert config is None
        return WasmModuleTypeDef(id, name, defined_at, wasm_file)

    decorator = ext_module_decorator(
        type_def_wrapper,
        WasmModuleInitCompiler(),
        WasmModuleDiscardCompiler(),
        True,
        wasm_sigs,
    )

    def inner_fun(ty: builtins.type[T]) -> GuppyDefinition:
        decorator_inner = decorator(str(wasm_path), None)
        return decorator_inner(ty)

    return inner_fun


def ext_module_decorator(
    type_def: Callable[[DefId, str, ast.AST | None, str, str | None], OpaqueTypeDef],
    init_compiler: CustomInoutCallCompiler,
    discard_compiler: CustomInoutCallCompiler,
    init_arg: bool,  # Whether the init function should take a nat argument
    wasm_sigs: ConcreteWasmModule
    | None = None,  # For @wasm_module, we must be passed a parsed wasm file
) -> Callable[[str, str | None], Callable[[builtins.type[T]], GuppyDefinition]]:
    def fun(
        filename: str, module: str | None
    ) -> Callable[[builtins.type[T]], GuppyDefinition]:
        @pretty_errors
        def dec(cls: builtins.type[T]) -> GuppyDefinition:
            # N.B. Only one module per file and vice-versa
            ext_module = type_def(
                DefId.fresh(),
                cls.__name__,
                None,
                filename,
                module,
            )

            ext_module_ty = ext_module.check_instantiate([], None)

            DEF_STORE.register_def(ext_module, get_calling_frame())
            for val in cls.__dict__.values():
                if isinstance(val, GuppyDefinition):
                    DEF_STORE.register_impl(ext_module.id, val.wrapped.name, val.id)
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
                                None, wasm_def.name, filename
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
                True,
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
                True,
            )
            DEF_STORE.register_def(call_method, get_calling_frame())
            DEF_STORE.register_impl(ext_module.id, "__new__", call_method.id)
            DEF_STORE.register_def(discard, get_calling_frame())
            DEF_STORE.register_impl(ext_module.id, "discard", discard.id)

            return GuppyDefinition(ext_module)

        return dec

    return fun


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
            return wasm_helper(arg, f)

        return wrapper
    else:
        return wasm_helper(None, arg)


def wasm_helper(fn_id: int | None, f: Callable[P, T]) -> GuppyFunctionDefinition[P, T]:
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
    custom_function = _dummy_custom_decorator
    hugr_op = _dummy_custom_decorator
    extend_type = _dummy_custom_decorator
    custom_type = _dummy_custom_decorator
    wasm_module = _dummy_custom_decorator
    wasm = _dummy_custom_decorator()
