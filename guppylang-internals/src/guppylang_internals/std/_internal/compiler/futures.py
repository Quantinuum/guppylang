from collections.abc import Callable, Sequence

from hugr import ops
from hugr import tys as ht

from guppylang_internals.error import InternalGuppyError
from guppylang_internals.std._internal.compiler.tket_exts import FUTURES_EXTENSION
from guppylang_internals.tys.arg import Argument, TypeArg
from guppylang_internals.tys.common import ToHugrContext
from guppylang_internals.tys.subst import Inst


def future_to_hugr(type_args: Sequence[Argument], ctx: ToHugrContext) -> ht.Type:
    match type_args:
        case [TypeArg(ty)]:
            type_def = FUTURES_EXTENSION.get_type("Future")
            return type_def.instantiate([ht.TypeTypeArg(ty.to_hugr(ctx))])
        case _:
            raise InternalGuppyError("Invalid type args for Future type")


def future_op(
    op_name: str,
) -> Callable[[ht.FunctionType, Inst, ToHugrContext], ops.DataflowOp]:
    op_def = FUTURES_EXTENSION.get_op(op_name)

    def op(concrete: ht.FunctionType, args: Inst, ctx: ToHugrContext) -> ops.DataflowOp:
        return op_def.instantiate([arg.to_hugr(ctx) for arg in args], concrete)

    return op
