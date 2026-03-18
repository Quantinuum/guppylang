from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.errors.wasm import (
    FirstArgNotModule,
    UnWasmableType,
)
from guppylang_internals.definition.custom import (
    CustomFunctionDef,
    RawCustomFunctionDef,
)
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.error import GuppyError, GuppyTypeError
from guppylang_internals.span import SourceMap
from guppylang_internals.tys.builtin import wasm_module_name
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
    TupleType,
    Type,
)
from guppylang_internals.wasm_util import WasmSigMismatchError

if TYPE_CHECKING:
    from guppylang_internals.checker.core import Globals


@dataclass(frozen=True)
class RawWasmFunctionDef(RawCustomFunctionDef):
    # If a function is specified in the @wasm decorator by its index in the wasm
    # file, record what the index was.
    wasm_index: int | None = field(default=None)

    def sanitise_type(self, loc: AstNode, fun_ty: FunctionType) -> None:
        # Place to highlight in error messages
        match fun_ty.inputs:
            case [FuncInput(ty=ty, flags=InputFlags.Inout), *args] if (
                wasm_module_name(ty) is not None
            ):
                for inp in args:
                    if not self.is_type_wasmable(inp.ty):
                        raise GuppyError(UnWasmableType(loc, inp.ty))
            case [FuncInput(ty=ty), *_]:
                raise GuppyError(
                    FirstArgNotModule(loc).add_sub_diagnostic(
                        FirstArgNotModule.GotOtherType(loc, ty)
                    )
                )
            case []:
                raise GuppyError(FirstArgNotModule(loc))
        if not self.is_type_wasmable(fun_ty.output):
            match fun_ty.output:
                case NoneType():
                    pass
                case _:
                    raise GuppyError(UnWasmableType(loc, fun_ty.output))

    def validate_type(self, loc: AstNode, fun_ty: FunctionType) -> None:
        type_in_wasm: FunctionType = DEF_STORE.wasm_functions[self.id]
        assert type_in_wasm is not None
        # Drop the first arg because it should be "self"
        expected_type = FunctionType(fun_ty.inputs[1:], fun_ty.output)

        if expected_type != type_in_wasm:
            raise GuppyTypeError(
                WasmSigMismatchError(loc)
                .add_sub_diagnostic(
                    WasmSigMismatchError.Declaration(None, declared=str(expected_type))
                )
                .add_sub_diagnostic(
                    WasmSigMismatchError.Actual(None, actual=str(type_in_wasm))
                )
            )

    def is_type_wasmable(self, ty: Type) -> bool:
        match ty:
            case NumericType():
                return True
            case TupleType(element_types=tys):
                return all(self.is_type_wasmable(ty) for ty in tys)

        return False

    def parse(self, globals: "Globals", sources: SourceMap) -> "CustomFunctionDef":
        parsed = super().parse(globals, sources)
        assert parsed.defined_at is not None
        self.sanitise_type(parsed.defined_at, parsed.ty)
        self.validate_type(parsed.defined_at, parsed.ty)
        return parsed
