"""Build a HUGR extension from the declarations harvested from a Python file."""

from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING, Any, cast

from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.ty import OpaqueTypeDef
from guppylang_internals.tys.common import Transformer
from guppylang_internals.tys.param import ConstParam, TypeParam
from guppylang_internals.tys.ty import BoundTypeVar, NumericType, OpaqueType
from hugr import tys as ht
from hugr.ext import ExplicitBound, Extension, OpDef, OpDefSig, TypeDef, Version

from auto_hugr_ext.state import EXTENSION_STATE

if TYPE_CHECKING:
    from guppylang_internals.tys.param import Parameter
    from guppylang_internals.tys.ty import FunctionType

    from auto_hugr_ext.harvest import ExtTypeEntry, HarvestedExtension


class _DummyToHugrContext:
    """`ToHugrContext` is an empty protocol, so no state is needed."""


TO_HUGR_CTX = _DummyToHugrContext()


@cache
def _var_type_def(idx: int, bound: ht.TypeBound) -> OpaqueTypeDef:
    linear = bound == ht.TypeBound.Linear
    return OpaqueTypeDef(
        DefId.fresh(),
        f"#{idx}",
        None,
        [],
        never_copyable=linear,
        never_droppable=linear,
        to_hugr=lambda args, ctx: ht.Variable(idx, bound),
        bound=bound,
    )


class _BoundVarSubstituter(Transformer):
    def transform(self, ty: Any) -> Any | None:
        if isinstance(ty, BoundTypeVar):
            return OpaqueType([], _var_type_def(ty.idx, ty.hugr_bound))
        return None


def param_to_hugr(param: Parameter) -> ht.TypeParam:
    match param:
        case TypeParam() as p:
            bound = ht.TypeBound.Linear if p.can_be_linear else ht.TypeBound.Copyable
            return ht.TypeTypeParam(bound)
        case ConstParam(ty=NumericType()):
            return ht.BoundedNatParam()
        case _:
            msg = f"Unsupported extension parameter: {param}"
            raise NotImplementedError(msg)


def func_ty_to_hugr(ty: FunctionType) -> ht.FunctionType | ht.PolyFuncType:
    mono = cast("FunctionType", ty.transform(_BoundVarSubstituter()))
    body = mono._to_hugr_function_type(TO_HUGR_CTX)
    if not ty.params:
        return body
    return ht.PolyFuncType(params=[param_to_hugr(p) for p in ty.params], body=body)


def type_def_to_hugr(entry: ExtTypeEntry) -> TypeDef:
    params = [param_to_hugr(param) for param in entry.defn.params]
    bound = (
        ht.TypeBound.Copyable
        if entry.copyable and entry.droppable
        else ht.TypeBound.Linear
    )
    return TypeDef(
        name=entry.name,
        description="",
        params=params,
        bound=ExplicitBound(bound),
    )


def build_extension(ext_name: str, harvested: HarvestedExtension) -> Extension:
    extension = Extension(ext_name, Version(0, 1, 0))
    for entry in harvested.types:
        extension.add_type_def(type_def_to_hugr(entry))

    EXTENSION_STATE.extension = extension
    for op in harvested.ops:
        signature = func_ty_to_hugr(op.ty)
        extension.add_op_def(
            OpDef(
                name=op.name,
                signature=OpDefSig(poly_func=signature),
                description="",
            )
        )
    return extension
