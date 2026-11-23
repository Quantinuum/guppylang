"""Compilers for trigonometric operations on Guppy angles."""

import math

from hugr import Wire
from hugr import ext as he
from hugr import tys as ht
from hugr.std.float import FLOAT_T, FloatVal

from guppylang_internals.compiler.builder import pure
from guppylang_internals.compiler.builder.ops import make_tuple, unpack_tuple
from guppylang_internals.definition.custom import CustomInoutCallCompiler
from guppylang_internals.definition.value import CallReturnWires


class TrigCompiler(CustomInoutCallCompiler):
    """Convert between Guppy half-turn angles and HUGR math radians."""

    def __init__(
        self,
        opname: str,
        *,
        math_extension: he.Extension,
        inverse: bool = False,
    ) -> None:
        self.opname = opname
        self.math_extension = math_extension
        self.inverse = inverse

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        from guppylang_internals.std._internal.util import float_op

        pi = self.builder.load(self.builder.add_const(FloatVal(math.pi)))
        binary_float = ht.FunctionType([FLOAT_T, FLOAT_T], [FLOAT_T])
        if not self.inverse:
            [angle] = args
            [halfturns] = self.builder.add_op(unpack_tuple([FLOAT_T]), angle)
            args = list(
                self.builder.add_op(
                    pure(float_op("fmul")(binary_float, (), self.ctx)),
                    halfturns,
                    pi,
                )
            )
        [result] = self.builder.add_op(
            pure(
                float_op(self.opname, self.math_extension)(
                    ht.FunctionType([FLOAT_T] * len(args), [FLOAT_T]), (), self.ctx
                )
            ),
            *args,
        )
        if self.inverse:
            [halfturns] = self.builder.add_op(
                pure(float_op("fdiv")(binary_float, (), self.ctx)), result, pi
            )
            [result] = self.builder.add_op(make_tuple([FLOAT_T]), halfturns)
        return CallReturnWires(regular_returns=[result], inout_returns=[])
