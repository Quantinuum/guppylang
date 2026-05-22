"""Compilers building list functions on top of hugr standard operations, that involve
multiple nodes.
"""

from __future__ import annotations

from hugr import Wire, ops
from hugr import ext as he
from hugr import tys as ht
from hugr.std.float import FLOAT_T

from guppylang_internals.definition.custom import CustomInoutCallCompiler
from guppylang_internals.definition.value import CallReturnWires
from guppylang_internals.std._internal.compiler.tket_exts import (
    FUTURES_EXTENSION,
    QSYSTEM_RANDOM_EXTENSION,
    QUANTUM_EXTENSION,
    ROTATION_EXTENSION,
)

# ----------------------------------------------
# --------- tket.* extensions -----------------
# ----------------------------------------------


RNGCONTEXT_T_DEF = QSYSTEM_RANDOM_EXTENSION.get_type("context")
RNGCONTEXT_T = ht.ExtType(RNGCONTEXT_T_DEF)

ROTATION_T_DEF = ROTATION_EXTENSION.get_type("rotation")
ROTATION_T = ht.ExtType(ROTATION_T_DEF)


def from_halfturns_unchecked() -> ops.ExtOp:
    return ops.ExtOp(
        ROTATION_EXTENSION.get_op("from_halfturns_unchecked"),
        ht.FunctionType([FLOAT_T], [ROTATION_T]),
    )


# ------------------------------------------------------
# --------- Custom compilers for non-native ops --------
# ------------------------------------------------------


class InoutMeasureCompiler(CustomInoutCallCompiler):
    """Compiler for the measure functions with an inout qubit."""

    opname: str
    ext: he.Extension
    return_future: bool

    def __init__(
        self,
        opname: str | None = None,
        ext: he.Extension | None = None,
        *,
        return_future: bool = False,
    ):
        """
        Args:
            opname: Name of operation to compile. Defaults to ``"Measure"``.
            ext: Extension that provides ``opname``. Defaults to ``QUANTUM_EXTENSION``.
            return_future: Whether `opname` returns a future instead of a bool as the
                measurement result.
        """
        self.opname = opname or "Measure"
        self.ext = ext or QUANTUM_EXTENSION
        self.return_future = return_future

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        from guppylang_internals.std._internal.util import quantum_op

        return_ty = (
            ht.Bool
            if not self.return_future
            else FUTURES_EXTENSION.get_type("Future").instantiate(
                [ht.TypeTypeArg(ht.Bool)]
            )
        )
        [q] = args
        [q, bit] = self.builder.add_op(
            quantum_op(self.opname, ext=self.ext)(
                ht.FunctionType([ht.Qubit], [ht.Qubit, return_ty]), (), self.ctx
            ),
            q,
        )
        return CallReturnWires(regular_returns=[bit], inout_returns=[q])


class RotationCompiler(CustomInoutCallCompiler):
    opname: str

    def __init__(self, opname: str):
        self.opname = opname

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        from guppylang_internals.std._internal.util import quantum_op

        [*qs, angle] = args
        [halfturns] = self.builder.add_op(ops.UnpackTuple([FLOAT_T]), angle)
        [rotation] = self.builder.add_op(from_halfturns_unchecked(), halfturns)

        qs = self.builder.add_op(
            quantum_op(self.opname)(
                ht.FunctionType(
                    [ht.Qubit for _ in qs] + [ROTATION_T], [ht.Qubit for _ in qs]
                ),
                (),
                self.ctx,
            ),
            *qs,
            rotation,
        )
        return CallReturnWires(regular_returns=[], inout_returns=list(qs))
