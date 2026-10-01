"""Lower pointer calls while preserving payload ownership and handle sequencing."""

from collections.abc import Sequence

from hugr import Wire
from hugr import tys as ht
from hugr.std.ptr import EXTENSION, Ptr

from guppylang_internals.compiler.expr_compiler import unpack_wire
from guppylang_internals.definition.custom import CustomInoutCallCompiler
from guppylang_internals.definition.value import CallReturnWires
from guppylang_internals.error import InternalGuppyError
from guppylang_internals.tys.arg import Argument, TypeArg
from guppylang_internals.tys.common import ToHugrContext


def ptr_to_hugr(type_args: Sequence[Argument], ctx: ToHugrContext) -> ht.Type:
    match type_args:
        case [TypeArg(ty)]:
            return Ptr(ty.to_hugr(ctx))
        case _:
            raise InternalGuppyError("Invalid type args for Ptr")


class PtrCompiler(CustomInoutCallCompiler):
    """Adapt pointer-first extension outputs to Guppy's trailing inout returns."""

    def __init__(self, name: str) -> None:
        self.name = name

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        # Use the concrete signature: method type variables can have different
        # declaration orders, and a tuple payload is one stored value, not a row.
        if self.name == "New":
            payload = self.ty.input[0]
        else:
            ptr = self.ty.input[0]
            assert isinstance(ptr, ht.ExtType)
            payload_arg = ptr.args[0]
            assert isinstance(payload_arg, ht.TypeTypeArg)
            payload = payload_arg.ty
        type_args: list[ht.TypeArg] = [ht.TypeTypeArg(payload)]
        if self.name == "Map":
            callback = self.ty.input[1]
            assert isinstance(callback, ht.FunctionType)
            type_args += [
                ht.ListArg([ht.TypeTypeArg(t) for t in callback.input[1:]]),
                ht.ListArg([ht.TypeTypeArg(t) for t in callback.output[1:]]),
            ]
        match self.name:
            case "New" | "Free":
                output = list(self.ty.output)
            case "Read" | "Swap":
                output = [self.ty.input[0], payload]
            case "Dup":
                output = [self.ty.input[0], self.ty.input[0]]
            case "Write":
                output = [self.ty.input[0]]
            case "Map":
                output = [self.ty.input[0], *callback.output[1:]]
            case _:
                raise InternalGuppyError(f"Unknown pointer operation {self.name}")
        signature = ht.FunctionType(list(self.ty.input), output)
        op = EXTENSION.get_op(self.name).instantiate(type_args, signature)
        outputs: list[Wire] = list(
            self.builder.add_op((op, self.func.call_effects), *args)
        )
        if self.name in {"New", "Free"}:
            return CallReturnWires(regular_returns=outputs, inout_returns=[])
        ptr_out, *regular = outputs
        if self.name in {"Read", "Swap", "Map"}:
            [result] = regular
            regular = unpack_wire(result, self.func.ty.output, self.builder, self.ctx)
        return CallReturnWires(regular_returns=regular, inout_returns=[ptr_out])
