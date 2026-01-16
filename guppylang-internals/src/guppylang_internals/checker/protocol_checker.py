from abc import ABC
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar, TypeAlias

from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.parameter import Error
from guppylang_internals.definition.protocol import CheckedProtocolDef
from guppylang_internals.engine import ENGINE
from guppylang_internals.error import GuppyError
from guppylang_internals.tys.arg import Argument, ConstArg, TypeArg
from guppylang_internals.tys.const import BoundConstVar
from guppylang_internals.tys.protocol import ProtocolInst
from guppylang_internals.tys.subst import Inst, PartialInst, Subst
from guppylang_internals.tys.ty import (
    BoundTypeVar,
    FunctionType,
    Type,
    unify,
)


@dataclass(frozen=True)
class ImplProofBase(ABC):
    proto: ProtocolInst
    ty: Type

    def __post_init__(self) -> None:
        assert all(not arg.unsolved_vars for arg in self.proto.type_args)


@dataclass(frozen=True)
class ConcreteImplProof(ImplProofBase):
    #: For each protocol member, the concrete function that implements it together with
    #: an instantiation of the type parameters of the implementation. This could refer
    #: to bound variables specified by the protocol method.
    #: If we have a protocol `def foo[T](x: T, y: int)` and implementation
    #: `def foo[A, B](x: A, y: B)`, then the instantiation will specify `A := T` and
    #: `B := int`.
    member_impls: Mapping[str, tuple[DefId, Inst]]

    # def __post_init__(self) -> None:
    #     assert self.member_impls.keys() == self.proto.members.keys()


@dataclass(frozen=True)
class AssumptionImplProof(ImplProofBase):
    ty: BoundTypeVar

    def __post_init__(self) -> None:
        super().__post_init__()
        assert self.proto in self.ty.implements


ImplProof: TypeAlias = ConcreteImplProof | AssumptionImplProof


@dataclass(frozen=True)
class ProtocolMemberMissing(Error):
    title: ClassVar[str] = "Protocol member implementation missing"
    span_label: ClassVar[str] = (
        "Type {impl_name} does not implement member {member_name} of "
        "protocol {proto_name}"
    )
    impl_name: str
    proto_name: str
    member_name: str


def _unify_args(
    xs: Sequence[Argument], ys: Sequence[Argument], subst: Subst | None
) -> Subst | None:
    for x, y in zip(xs, ys, strict=True):
        # TODO: Unify doesn't expect arguments here
        subst = unify(x, y, subst)
        if subst is None:
            return None
    return subst


def _instantiate_self(
    proto_func: FunctionType, proto_inst: ProtocolInst, impl_ty: Type
) -> FunctionType:
    # Assumption: first argument must be self.
    self_ty = proto_func.inputs[0].ty
    assert isinstance(self_ty, BoundTypeVar)
    [bound] = self_ty.implements
    assert bound.def_id == proto_inst.def_id
    partial_inst: PartialInst = [None for _ in proto_func.params]
    # Instantiate all self type occurrences in protocol methods with the type we assume
    # is implementing the protocol.
    for proto_arg, bound_arg in zip(proto_inst.type_args, bound.type_args, strict=True):
        match bound_arg:
            case TypeArg(ty=BoundTypeVar(idx=idx)):
                partial_inst[idx] = proto_arg
            case ConstArg(const=BoundConstVar(idx=idx)):
                partial_inst[idx] = proto_arg
    partial_inst[self_ty.idx] = impl_ty.to_arg()
    return proto_func.instantiate_partial(partial_inst)

def _substitute_proto_inst_args(proto: ProtocolInst, subst: Subst) -> ProtocolInst:
    # TODO: Implement substitution of type arguments
    return proto


def check_protocol(ty: Type, protocol: ProtocolInst) -> tuple[ImplProof, Subst]:
    # Invariant: `ty` and `protocol` might have unsolved variables.
    protocol_def = ENGINE.get_checked(protocol.def_id)
    assert isinstance(protocol_def, CheckedProtocolDef)

    if isinstance(ty, BoundTypeVar):
        candidates = []
        for impl in ty.implements:
            if impl.def_id == protocol.def_id:
                # TODO: Should either be existential or concrete.
                subst = _unify_args(protocol.type_args, impl.type_args, {})
                if subst is not None:
                    candidates.append((impl, subst))
        if len(candidates) != 1:
            raise Exception("Zero or more than one")
        [(_, subst)] = candidates
        return AssumptionImplProof(
            _substitute_proto_inst_args(protocol, subst),
            ty.substitute(subst),
        ), subst

    subst = {}
    member_impls = {}
    for name, proto_sig in protocol_def.members.items():
        assert isinstance(proto_sig, FunctionType)
        # Partially instantiate proto_sig with `protocol.type_args` and `ty`.
        proto_sig = _instantiate_self(proto_sig, protocol, ty)
        func = ENGINE.get_instance_func(ty, name)
        if not func:
            raise GuppyError(
                ProtocolMemberMissing(
                    impl_name=ty.display_name,
                    proto_name=protocol_def.name,
                    member_name=name,
                )
            )
        # Make type variables in implementation signature existential for unification.
        impl_sig, impl_vars = func.ty.unquantified()
        # Make parameters in protocol signature unbound for unification.
        proto_sig = FunctionType(proto_sig.inputs, proto_sig.output, params=[])
        # Try to unify both signatures.
        subst = unify(proto_sig, impl_sig, subst)
        if subst is None:
            raise Exception("Signature Mismatch")
        if any(x not in subst for x in impl_vars):
            raise Exception("Unresolved variables in implementation")
        member_impls[name] = (func.id, [subst[x] for x in impl_vars])

    if any(x not in subst for arg in protocol.type_args for x in arg.unsolved_vars):
        raise Exception("Couldn't figure out variables in protocol")
    subst = {x: subst[x] for arg in protocol.type_args for x in arg.unsolved_vars}
    return ConcreteImplProof(protocol, ty, member_impls), subst
