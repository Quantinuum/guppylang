from hugr import ops as hops
from hugr.tys import Sum, Type, TypeRow

from guppylang_internals.compiler.builder import OpWithEffects, Pure


def make_tuple(tys: TypeRow | None = None) -> OpWithEffects:
    return Pure(hops.MakeTuple(tys))


def unpack_tuple(tys: TypeRow | None = None) -> OpWithEffects:
    return Pure(hops.UnpackTuple(tys))


def tag(tag: int, rows: Sum) -> OpWithEffects:
    return Pure(hops.Tag(tag, rows))


def some(ty: Type) -> OpWithEffects:
    return Pure(hops.Some(ty))
