from hugr import ops
from hugr import tys as ht
from hugr.tys import TypeRow

from guppylang_internals.compiler.builder import OpWithEffects, pure


def MakeTuple(tys: TypeRow | None = None) -> OpWithEffects:
    return pure(ops.MakeTuple(tys))


def UnpackTuple(tys: TypeRow | None = None) -> OpWithEffects:
    return pure(ops.UnpackTuple(tys))


def Tag(tag: int, rows: ht.Sum) -> OpWithEffects:
    return pure(ops.Tag(tag, rows))


def Some(ty: ht.Type) -> OpWithEffects:
    return pure(ops.Some(ty))
