import functools
from collections.abc import Sequence
from typing import Any

from guppylang_internals.error import InternalGuppyError
from guppylang_internals.tys.arg import Argument, ConstArg, TypeArg
from guppylang_internals.tys.common import Transformer
from guppylang_internals.tys.const import (
    BoundConstVar,
    Const,
    ConstBase,
    ExistentialConstVar,
)
from guppylang_internals.tys.ty import (
    BoundTypeVar,
    ExistentialTypeVar,
    FunctionType,
    Type,
    TypeBase,
)
from guppylang_internals.tys.var import ExistentialVar

Subst = dict[ExistentialVar, Type | Const]
Inst = Sequence[Argument]
PartialInst = Sequence["Argument | None"]


class Substituter(Transformer):
    """Type transformer that applies a substitution of existential variables."""

    def __init__(self, subst: Subst) -> None:
        self.subst = subst

    @functools.singledispatchmethod
    def transform(self, ty: Any) -> Any | None:
        return None

    @transform.register
    def _transform_ExistentialTypeVar(self, ty: ExistentialTypeVar) -> Type | None:
        s = self.subst.get(ty, None)
        assert not isinstance(s, ConstBase)
        return s

    @transform.register
    def _transform_ExistentialConstVar(self, c: ExistentialConstVar) -> Const | None:
        s = self.subst.get(c, None)
        assert not isinstance(s, TypeBase)
        return s


class Instantiator(Transformer):
    """Type transformer that instantiates bound variables."""

    def __init__(self, inst: PartialInst, allow_partial: bool = False) -> None:
        self.allow_partial = allow_partial
        self.inst = inst

    @functools.singledispatchmethod
    def transform(self, ty: Any) -> Any | None:
        return None

    @transform.register
    def _transform_BoundTypeVar(self, ty: BoundTypeVar) -> Type | None:
        # Instantiate if type for the index is available
        if ty.idx < len(self.inst):
            arg = self.inst[ty.idx]
            if arg is None and self.allow_partial:
                return None
            assert isinstance(arg, TypeArg)
            return arg.ty

        # Otherwise, lower the de Bruijn index
        return BoundTypeVar(
            ty.display_name, ty.idx - len(self.inst), ty.copyable, ty.droppable
        )

    @transform.register
    def _transform_BoundConstVar(self, c: BoundConstVar) -> Const | None:
        # Instantiate if const value for the index is available
        if c.idx < len(self.inst):
            arg = self.inst[c.idx]
            if arg is None and self.allow_partial:
                return None
            assert isinstance(arg, ConstArg)
            return arg.const

        # Otherwise, lower the de Bruijn index
        return BoundConstVar(c.ty, c.display_name, c.idx - len(self.inst))

    @transform.register
    def _transform_FunctionType(self, ty: FunctionType) -> Type | None:
        if ty.parametrized:
            raise InternalGuppyError("Tried to instantiate under binder")
        return None
