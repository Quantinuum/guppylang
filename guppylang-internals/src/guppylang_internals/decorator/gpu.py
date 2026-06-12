from __future__ import annotations

from typing import TYPE_CHECKING, ParamSpec, TypeVar, overload

from guppylang_internals.compiler.core import GlobalConstId
from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.custom import (
    CustomFunctionDef,
    CustomInoutCallCompiler,
    DefaultCallChecker,
)
from guppylang_internals.definition.gpu import GpuModuleTypeDef, RawGpuFunctionDef
from guppylang_internals.dummy_decorator import _dummy_custom_decorator, sphinx_running
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.frame_util import get_calling_frame
from guppylang_internals.std._internal.compiler.gpu import (
    GpuModuleCallCompiler,
    GpuModuleDiscardCompiler,
    GpuModuleInitCompiler,
)
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
)

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
        id: DefId,
        name: str,
        defined_at: ast.AST | None,
        gpu_file: str,
        gpu_config: str | None,
    ) -> OpaqueTypeDef:
        return GpuModuleTypeDef(id, name, defined_at, gpu_file, gpu_config)

    f = ext_module_decorator(
        type_def_wrapper, GpuModuleInitCompiler(), GpuModuleDiscardCompiler(), False
    )
    return f(filename, config_filename)


def ext_module_decorator(
    type_def: Callable[[DefId, str, ast.AST | None, str, str | None], OpaqueTypeDef],
    init_compiler: CustomInoutCallCompiler,
    discard_compiler: CustomInoutCallCompiler,
    init_arg: bool,  # Whether the init function should take a nat argument
) -> Callable[[str, str | None], Callable[[builtins.type[T]], GuppyDefinition]]:
    from guppylang.defs import GuppyDefinition

    def fun(
        filename: str, module: str | None
    ) -> Callable[[builtins.type[T]], GuppyDefinition]:
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
                    DEF_STORE.register_type_member(
                        ext_module.id, val.wrapped.name, val.id
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
                call_checker=DefaultCallChecker(),
                call_compiler=init_compiler,
                higher_order_value=True,
                higher_order_func_id=GlobalConstId.fresh(f"{cls.__name__}.__new__"),
                has_signature=True,
                has_var_args=False,
            )
            discard = CustomFunctionDef(
                DefId.fresh(),
                "discard",
                None,
                FunctionType([FuncInput(ext_module_ty, InputFlags.Owned)], NoneType()),
                call_checker=DefaultCallChecker(),
                call_compiler=discard_compiler,
                higher_order_value=False,
                higher_order_func_id=GlobalConstId.fresh(f"{cls.__name__}.__discard__"),
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
