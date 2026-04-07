from hugr import Wire
from hugr import tys as ht
from hugr.std.int import int_t

from guppylang_internals.definition.custom import CustomInoutCallCompiler
from guppylang_internals.definition.value import CallReturnWires
from guppylang_internals.std._internal.compiler.arithmetic import inarrow_s, iwiden_s
from guppylang_internals.std._internal.compiler.prelude import build_unwrap_right
from guppylang_internals.std._internal.compiler.quantum import (
    RNGCONTEXT_T,
)
from guppylang_internals.std._internal.compiler.tket_bool import make_opaque
from guppylang_internals.std._internal.compiler.tket_exts import (
    FUTURES_EXTENSION,
    QSYSTEM_EXTENSION,
    QSYSTEM_RANDOM_EXTENSION,
)
from guppylang_internals.std._internal.util import external_op, quantum_op


class RandomIntCompiler(CustomInoutCallCompiler):
    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [ctx] = args
        [rnd, ctx] = self.builder.add_op(
            external_op("RandomInt", [], ext=QSYSTEM_RANDOM_EXTENSION)(
                ht.FunctionType([RNGCONTEXT_T], [int_t(5), RNGCONTEXT_T]), (), self.ctx
            ),
            ctx,
        )
        [rnd] = self.builder.add_op(iwiden_s(5, 6), rnd)
        return CallReturnWires(regular_returns=[rnd], inout_returns=[ctx])


class RandomIntBoundedCompiler(CustomInoutCallCompiler):
    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [ctx, bound] = args
        bound_sum = self.builder.add_op(inarrow_s(6, 5), bound)
        bound = build_unwrap_right(
            self.builder, bound_sum, "bound must be a 32-bit integer"
        )
        [rnd, ctx] = self.builder.add_op(
            external_op("RandomIntBounded", [], ext=QSYSTEM_RANDOM_EXTENSION)(
                ht.FunctionType([RNGCONTEXT_T, int_t(5)], [int_t(5), RNGCONTEXT_T]),
                (),
                self.ctx,
            ),
            ctx,
            bound,
        )
        [rnd] = self.builder.add_op(iwiden_s(5, 6), rnd)
        return CallReturnWires(regular_returns=[rnd], inout_returns=[ctx])


class LazyMeasureResetCompiler(CustomInoutCallCompiler):
    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [q] = args
        [q, measurement] = self.builder.add_op(
            quantum_op("LazyMeasureReset", ext=QSYSTEM_EXTENSION)(
                ht.FunctionType([ht.Qubit], [ht.Qubit, future_bool_type()]),
                (),
                self.ctx,
            ),
            q,
        )
        return CallReturnWires(regular_returns=[measurement], inout_returns=[q])


def future_bool_type() -> ht.ExtType:
    return FUTURES_EXTENSION.get_type("Future").instantiate([ht.TypeTypeArg(ht.Bool)])


class ReadFutureBoolCompiler(CustomInoutCallCompiler):
    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [future] = args
        [bool_value] = self.builder.add_op(
            FUTURES_EXTENSION.get_op("Read").instantiate(
                [ht.TypeTypeArg(ht.Bool)],
                ht.FunctionType([future_bool_type()], [ht.Bool]),
            ),
            future,
        )
        opaque_bool_value = self.builder.add_op(make_opaque(), bool_value)
        return CallReturnWires(regular_returns=[opaque_bool_value], inout_returns=[])
