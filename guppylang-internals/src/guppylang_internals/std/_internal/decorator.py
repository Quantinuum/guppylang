import ast
import builtins
from collections.abc import Callable
from typing import Protocol, TypeVar

from guppylang.defs import GuppyDefinition

from guppylang_internals.compiler.core import GlobalConstId
from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.custom import (
    CustomFunctionDef,
    CustomInoutCallCompiler,
    DefaultCallChecker,
)
from guppylang_internals.definition.ty import OpaqueTypeDef
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.error import pretty_errors
from guppylang_internals.frame_util import get_calling_frame
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
)

T = TypeVar("T")
T2 = TypeVar("T2", contravariant=True)


class CreateTypeDef(Protocol):
    def __call__(
        self,
        def_id: DefId,
        name: str,
        defined_at: ast.AST | None,
        filename: str,
        config_filename: str | None,
    ) -> OpaqueTypeDef: ...


class CreateModuleDecorator(Protocol[T2]):
    def __call__(
        self, filename: str, config_filename: str | None
    ) -> Callable[[builtins.type[T2]], GuppyDefinition]: ...


def ext_module_decorator(
    create_type_def: CreateTypeDef,
    init_compiler: CustomInoutCallCompiler,
    discard_compiler: CustomInoutCallCompiler,
    init_arg: bool,  # Whether the init function should take a nat argument
    foreach_member: Callable[[GuppyDefinition], None] = lambda _: None,
) -> CreateModuleDecorator[T]:
    def fun(
        filename: str, config_filename: str | None
    ) -> Callable[[builtins.type[T]], GuppyDefinition]:
        @pretty_errors
        def dec(cls: builtins.type[T]) -> GuppyDefinition:
            # N.B. Only one module per file and vice-versa
            ext_module = create_type_def(
                DefId.fresh(),
                cls.__name__,
                None,
                filename,
                config_filename,
            )

            ext_module_ty = ext_module.check_instantiate([], None)

            DEF_STORE.register_def(ext_module, get_calling_frame())
            for val in cls.__dict__.values():
                if isinstance(val, GuppyDefinition):
                    DEF_STORE.register_type_member(
                        ext_module.id, val.wrapped.name, val.id
                    )
                    foreach_member(val)

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
