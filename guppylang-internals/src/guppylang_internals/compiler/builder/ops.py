from hugr import ops
from hugr.tys import Sum, Type, TypeRow

from guppylang_internals.compiler.builder import OpWithEffects, pure


def make_tuple(tys: TypeRow | None = None) -> OpWithEffects:
    return pure(ops.MakeTuple(tys))


def unpack_tuple(tys: TypeRow | None = None) -> OpWithEffects:
    return pure(ops.UnpackTuple(tys))


def tag(tag: int, rows: Sum) -> OpWithEffects:
    return pure(ops.Tag(tag, rows))


def some(ty: Type) -> OpWithEffects:
    return pure(ops.Some(ty))
