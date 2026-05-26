from abc import ABC
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TypeAlias

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.errors.type_errors import (
    AmbiguousProtocol,
    CouldntInferProtoArgs,
    DoesntImplementProtocol,
    FirstArgNotProtocol,
    ProtocolMemberMissing,
    SignatureDoesntMatchProto,
)
from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.protocol import CheckedProtocolDef
from guppylang_internals.engine import ENGINE
from guppylang_internals.error import GuppyError
from guppylang_internals.tys.arg import Argument, ConstArg, TypeArg
from guppylang_internals.tys.const import BoundConstVar, ExistentialConstVar
from guppylang_internals.tys.protocol import ProtocolInst
from guppylang_internals.tys.subst import Inst, Subst, Substituter
from guppylang_internals.tys.ty import (
    BoundTypeVar,
    ExistentialTypeVar,
    FunctionType,
    Type,
    unify,
    unify_type_args,
)
from guppylang_internals.tys.var import ExistentialVar


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


@dataclass(frozen=True)
class AssumptionImplProof(ImplProofBase):
    ty: BoundTypeVar

    def __post_init__(self) -> None:
        super().__post_init__()


ImplProof: TypeAlias = ConcreteImplProof | AssumptionImplProof


def _unify_args(
    xs: Sequence[ExistentialVar], ys: Sequence[Argument], subst: Subst | None
) -> Subst | None:
    for x, y in zip(xs, ys, strict=True):
        match x, y:
            case ExistentialTypeVar(), TypeArg(ty=ty):
                subst = unify(x, ty, subst)
            case ExistentialConstVar(), ConstArg(const=const):
                subst = unify(x, const, subst)
            case _:
                return None  # Kind mismatch
    return subst


def _instantiate_self(
    proto_func: FunctionType, proto_inst: ProtocolInst, impl_ty: Type
) -> FunctionType:
    # Invariant: proto_func must have non-zero inputs, and the first input must
    # be a BoundVar representing the "self" of the protocol method.
    self_ty = proto_func.inputs[0].ty
    assert isinstance(self_ty, BoundTypeVar)
    for proto_bound in self_ty.implements:
        if proto_bound.def_id == proto_inst.def_id:
            # A mutable PartialInst
            partial_inst: list[Argument | None] = [None for _ in proto_func.params]
            # Instantiate all self type occurrences in protocol methods with the type we
            # assume is implementing the protocol.
            for proto_arg, bound_arg in zip(
                proto_inst.type_args, proto_bound.type_args, strict=True
            ):
                match bound_arg:
                    case TypeArg(ty=BoundTypeVar(idx=idx)):
                        partial_inst[idx] = proto_arg
                    case ConstArg(const=BoundConstVar(idx=idx)):
                        partial_inst[idx] = proto_arg
            partial_inst[self_ty.idx] = impl_ty.to_arg()
            return proto_func.instantiate_partial(partial_inst)
    from guppylang_internals.engine import ENGINE

    protocol = ENGINE.get_parsed(proto_inst.def_id)
    raise GuppyError(FirstArgNotProtocol(None, protocol.name))


def check_protocol(
    ty: Type, protocol: ProtocolInst, loc: AstNode | None = None
) -> tuple[ImplProof, Subst]:
    """Check that `ty` implements `protocol`"""

    # Invariant: `ty` and `protocol` might have unsolved variables.
    protocol_def = ENGINE.get_checked(protocol.def_id, protocol.type_args)
    assert isinstance(protocol_def, CheckedProtocolDef)

    # If `ty` is a bound type variable, we try to handle the case
    # `def foo[T, MyProto: Proto[T]](MyProto, ...) -> ...`
    # ... we must assume that bound variable `MyProto` implements `Proto[T]`
    # when `check_protocol` is invoked for this definition.
    if isinstance(ty, BoundTypeVar):
        # Iterate over all of the "must implement" bounds for `ty`, and collect
        # the ones that result in an implementation of `protocol`.
        # We hope there's only one answer!
        candidates: list[tuple[ProtocolInst, Subst]] = []
        for impl in ty.implements:
            if impl.def_id == protocol.def_id:
                subst = unify_type_args(protocol.type_args, impl.type_args, {})
                if subst is not None:
                    candidates.append((impl, subst))
        if len(candidates) == 0:
            raise GuppyError(
                DoesntImplementProtocol(
                    loc or protocol_def.defined_at, str(ty), protocol_def.name
                )
            )
        elif len(candidates) > 1:
            raise GuppyError(
                AmbiguousProtocol(
                    loc or protocol_def.defined_at, str(ty), protocol_def.name
                )
            )
        [(_, subst)] = candidates
        new_ty = ty.substitute(subst)
        assert isinstance(new_ty, BoundTypeVar)
        return AssumptionImplProof(
            protocol.transform(Substituter(subst)),
            new_ty,
        ), subst

    subst = {}
    member_impls: dict[str, tuple[DefId, Inst]] = {}
    for name in protocol_def.member_defs:
        proto_sig = protocol_def.member_sig(name)
        if len(proto_sig.inputs) > 0:
            if isinstance(proto_sig.inputs[0].ty, BoundTypeVar):
                proto_sig = _instantiate_self(proto_sig, protocol, ty)
            else:
                raise GuppyError(FirstArgNotProtocol(None, protocol_def.name))
                proto_sig = _instantiate_self(proto_sig, protocol, ty)
        func = ENGINE.get_instance_func(ty, name)
        if not func:
            raise GuppyError(
                ProtocolMemberMissing(
                    loc,
                    impl_name=str(ty),
                    proto_name=protocol_def.name,
                    member_name=name,
                )
            )
        # Make type variables in implementation signature existential for unification.
        impl_sig, ex_impl_vars = func.ty.unquantified()
        # Make parameters in protocol signature unbound for unification.
        proto_sig = FunctionType(proto_sig.inputs, proto_sig.output, params=[])
        # Try to unify both signatures.
        subst = unify(proto_sig, impl_sig, subst)
        if subst is None:
            raise GuppyError(SignatureDoesntMatchProto(loc, name))
        if any(x not in subst for x in ex_impl_vars):
            err = CouldntInferProtoArgs(loc, protocol_def.name)
            bad_args = [arg for arg in ex_impl_vars if arg not in subst]
            for arg in bad_args:
                err.add_sub_diagnostic(
                    CouldntInferProtoArgs.UnresolvedArg(None, str(arg))
                )
            raise GuppyError(err)
        # Turn these into type vars
        impl_vars: Inst = tuple(subst[var].to_arg() for var in ex_impl_vars)
        member_impls[name] = func.id, impl_vars

    if any(x not in subst for arg in protocol.type_args for x in arg.unsolved_vars):
        raise GuppyError(CouldntInferProtoArgs(loc, protocol_def.name))
    subst = {x: subst[x] for arg in protocol.type_args for x in arg.unsolved_vars}
    return ConcreteImplProof(
        protocol.transform(Substituter(subst)), ty, member_impls
    ), subst
