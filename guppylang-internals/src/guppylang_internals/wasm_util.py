from dataclasses import dataclass
from typing import ClassVar

import wasmtime as wt

from guppylang_internals.diagnostic import Error, Note
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
    Type,
)


# The thing to be imported elsewhere
@dataclass
class ConcreteWasmModule:
    filename: str
    # Function names in order for looking up by index
    functions: list[str]
    function_sigs: dict[str, FunctionType | str]


@dataclass(frozen=True)
class WasmSignatureError(Error):
    title: ClassVar[str] = (
        "Invalid signature for @wasm function `{fn_name}`\nin wasm file:\n`{filename}`"
    )
    fn_name: str
    filename: str

    @dataclass(frozen=True)
    class Message(Note):
        message = "{msg}"
        msg: str


@dataclass(frozen=True)
class WasmFileNotFound(Error):
    title: ClassVar[str] = "Wasm file `{file}` not found"
    file: str


@dataclass(frozen=True)
class WasmFunctionNotInFile(Error):
    title: ClassVar[str] = (
        "Declared wasm function `{function}` isn't exported by wasm file"
    )
    function: str

    @dataclass(frozen=True)
    class WasmFileNote(Note):
        message: ClassVar[str] = "Wasm file:\n`{filename}`"
        filename: str


@dataclass(frozen=True)
class WasmSigMismatchError(Error):
    title: ClassVar[str] = "Wasm signature mismatch"
    span_label: ClassVar[str] = (
        "Signature of wasm function didn't match that in provided wasm file"
    )

    @dataclass(frozen=True)
    class Declaration(Note):
        message: ClassVar[str] = "Declared signature: {declared}"
        declared: str

    @dataclass(frozen=True)
    class Actual(Note):
        message: ClassVar[str] = "Signature in wasm:  {actual}"
        actual: str


def decode_type(ty: wt.ValType) -> Type | None:
    if ty == wt.ValType.i64():
        return NumericType(NumericType.Kind.Int)
    elif ty == wt.ValType.f64():
        return NumericType(NumericType.Kind.Float)
    else:
        return None


def decode_sig(
    params: list[wt.ValType], output: wt.ValType | None
) -> FunctionType | str:
    # Function args in wasm are called "params"
    my_params: list[FuncInput] = []
    for p in params:
        if ty := decode_type(p):
            my_params.append(FuncInput(ty, flags=InputFlags.NoFlags))
        else:
            return f"Unsupported input type: {p}"
    if output:
        if ty := decode_type(output):
            return FunctionType(my_params, ty)
        else:
            return f"Unsupported output type: {output}"
    else:
        return FunctionType(my_params, NoneType())


def decode_wasm_functions(filename: str) -> ConcreteWasmModule:
    engine = wt.Engine()
    mod = wt.Module.from_file(engine, filename)

    functions: list[str] = []
    function_sigs: dict[str, FunctionType | str] = {}
    for fn in mod.exports:
        functions.append(fn.name)
        match fn.type:
            case wt.FuncType() as fun_ty:
                match fun_ty.results:
                    case []:
                        data = decode_sig(fun_ty.params, None)
                    case [output]:
                        data = decode_sig(fun_ty.params, output)
                    case _multi:
                        data = (
                            f"Multiple output types unsupported in function `{fn.name}`"
                        )
            case _:
                data = f"`{fn.name}` is not exported as a function"
        function_sigs[fn.name] = data

    return ConcreteWasmModule(filename, functions, function_sigs)
