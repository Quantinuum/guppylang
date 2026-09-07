from hugr import ops as hops
from hugr.tys import Sum, Type, TypeRow

from guppylang_internals.compiler.builder import OpWithEffects, pure


def make_tuple(tys: TypeRow | None = None) -> OpWithEffects:
    return pure(hops.MakeTuple(tys))


def unpack_tuple(tys: TypeRow | None = None) -> OpWithEffects:
    return pure(hops.UnpackTuple(tys))


def tag(tag: int, rows: Sum) -> OpWithEffects:
    return pure(hops.Tag(tag, rows))


def some(ty: Type) -> OpWithEffects:
    return pure(hops.Some(ty))
