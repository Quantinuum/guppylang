from hugr import ops
from hugr.tys import Sum, Type, TypeRow

from guppylang_internals.compiler.builder import OpWithEffects, Pure


def make_tuple(tys: TypeRow | None = None) -> OpWithEffects:
    return Pure(ops.MakeTuple(tys))


def unpack_tuple(tys: TypeRow | None = None) -> OpWithEffects:
    return Pure(ops.UnpackTuple(tys))


def tag(tag: int, rows: Sum) -> OpWithEffects:
    return Pure(ops.Tag(tag, rows))


def some(ty: Type) -> OpWithEffects:
    return Pure(ops.Some(ty))
