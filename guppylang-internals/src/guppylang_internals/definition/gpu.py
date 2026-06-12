import ast
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from hugr import tys as ht
from hugr import val
from tket_exts import gpu

from guppylang_internals.ast_util import AstNode
from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.custom import (
    CustomFunctionDef,
    RawCustomFunctionDef,
)
from guppylang_internals.definition.ty import OpaqueTypeDef
from guppylang_internals.error import GuppyError
from guppylang_internals.span import SourceMap
from guppylang_internals.std._internal.gpu import FirstArgNotModule, UnconvertibleType
from guppylang_internals.tys.arg import ConstArg, TypeArg
from guppylang_internals.tys.common import ToHugrContext
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
    OpaqueType,
    Type,
)

if TYPE_CHECKING:
    from guppylang_internals.checker.core import Globals

QSYSTEM_GPU_EXTENSION = gpu()


class RawGpuFunctionDef(RawCustomFunctionDef):
    def sanitise_type(self, loc: AstNode | None, fun_ty: FunctionType) -> None:
        # Place to highlight in error messages
        match fun_ty.inputs[0]:
            case FuncInput(ty=ty, flags=InputFlags.Inout) if (
                gpu_module_info(ty) is not None
            ):
                pass
            case FuncInput(ty=ty):
                raise GuppyError(FirstArgNotModule(loc, ty))
        for inp in fun_ty.inputs[1:]:
            if not self.is_valid_gpu_type(inp.ty):
                raise GuppyError(UnconvertibleType(loc, inp.ty))
        if not self.is_valid_gpu_type(fun_ty.output):
            match fun_ty.output:
                case NoneType():
                    pass
                case _:
                    raise GuppyError(UnconvertibleType(loc, fun_ty.output))

    def is_valid_gpu_type(self, ty: Type) -> bool:
        match ty:
            case NumericType():
                return True

        return False

    def parse(self, globals: "Globals", sources: SourceMap) -> "CustomFunctionDef":
        parsed = super().parse(globals, sources)
        self.sanitise_type(parsed.defined_at, parsed.ty)
        return parsed


@dataclass(frozen=True)
class ConstGpuModule(val.ExtensionValue):
    """Python wrapper for the tket ConstGpuModule type."""

    gpu_file: str
    gpu_config: str | None

    def to_value(self) -> val.Extension:
        ty = QSYSTEM_GPU_EXTENSION.get_type("module").instantiate([])

        name = "ConstGpuModule"
        payload = {
            "module_filename": self.gpu_file,
            "config_filename": self.gpu_config,
        }
        return val.Extension(name, typ=ty, val=payload)

    def __str__(self) -> str:
        return (
            f"tket.gpu.module(gpu_file={self.gpu_file}, gpu_config={self.gpu_config})"
        )


class GpuModuleTypeDef(OpaqueTypeDef):
    # Identify the module to load
    gpu_file: str
    # Identify the config file to load
    gpu_config: str | None

    def __init__(
        self,
        id: DefId,
        name: str,
        defined_at: ast.AST | None,
        gpu_file: str,
        gpu_config: str | None = None,
    ) -> None:
        super().__init__(id, name, defined_at, [], True, True, self.to_hugr)
        self.gpu_file: str = gpu_file
        self.gpu_config: str = gpu_config

    def to_hugr(
        self, args: Sequence[TypeArg | ConstArg], _: ToHugrContext, /
    ) -> ht.Type:
        assert args == []
        ty = QSYSTEM_GPU_EXTENSION.get_type("context")
        return ty.instantiate([])


def gpu_module_info(ty: Type) -> tuple[str, str | None] | None:
    if isinstance(ty, OpaqueType) and isinstance(ty.defn, GpuModuleTypeDef):
        return ty.defn.gpu_file, ty.defn.gpu_config
    return None
