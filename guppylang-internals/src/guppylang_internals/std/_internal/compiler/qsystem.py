from typing import no_type_check

from hugr import Wire
from hugr import tys as ht
from hugr.std.int import int_t

from guppylang_internals.decorator import custom_type, hugr_op
from guppylang_internals.definition.custom import CustomInoutCallCompiler
from guppylang_internals.definition.value import CallReturnWires
from guppylang_internals.std._internal.compiler.arithmetic import inarrow_s, iwiden_s
from guppylang_internals.std._internal.compiler.prelude import build_unwrap_right
from guppylang_internals.std._internal.compiler.quantum import (
    RNGCONTEXT_T,
)
from guppylang_internals.std._internal.compiler.tket_bool import make_opaque
from guppylang_internals.std._internal.compiler.tket_exts import (
    QSYSTEM_RANDOM_EXTENSION,
)
from guppylang_internals.std._internal.util import external_op


class RandomIntCompiler(CustomInoutCallCompiler):
    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [ctx] = args
        [rnd, ctx] = self.builder.add_op(
            external_op("RandomInt", [], ext=QSYSTEM_RANDOM_EXTENSION)(
                ht.FunctionType([RNGCONTEXT_T], [int_t(5), RNGCONTEXT_T]), [], self.ctx
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
                [],
                self.ctx,
            ),
            ctx,
            bound,
        )
        [rnd] = self.builder.add_op(iwiden_s(5, 6), rnd)
        return CallReturnWires(regular_returns=[rnd], inout_returns=[ctx])


@custom_type(ht.Bool)
class Bool:
    """Temporary hack allowing sum bools to be represented in the Guppy guppy type
    system alongside opaque bools."""

    @hugr_op(lambda _concrete, _args, _ctx: make_opaque())
    @no_type_check
    def make_opaque(self: "Bool") -> bool:
        """Make a sum bool from an opaque bool."""
