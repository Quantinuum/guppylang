import ast
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, TypeGuard

import hugr.std
import hugr.std.collections.array
import hugr.std.collections.list
from hugr import tys as ht

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.errors.type_errors import (
    DoesntImplementProtocol,
    FunctionPointerNotModifiableHint,
    UnitaryFlagMismatchHint,
)
from guppylang_internals.definition.common import CompiledDef, DefId
from guppylang_internals.definition.protocol import CheckedProtocolDef
from guppylang_internals.definition.ty import OpaqueTypeDef, TypeDef
from guppylang_internals.error import GuppyError, InternalGuppyError
from guppylang_internals.experimental import check_lists_enabled
from guppylang_internals.span import ToSpan
from guppylang_internals.std._internal.compiler.tket_exts import WASM_EXTENSION
from guppylang_internals.std._internal.wasm import WasmPlatform
from guppylang_internals.tys.arg import Argument, ConstArg, TypeArg
from guppylang_internals.tys.common import ToHugrContext, Transformer
from guppylang_internals.tys.const import Const, ConstValue
from guppylang_internals.tys.errors import WrongNumberOfTypeArgsError
from guppylang_internals.tys.param import ConstParam, Parameter, TypeParam
from guppylang_internals.tys.protocol import ProtocolInst
from guppylang_internals.tys.subst import Substituter
from guppylang_internals.tys.ty import (
    BoundTypeVar,
    FunctionDefType,
    FunctionType,
    NoneType,
    NumericType,
    OpaqueType,
    TupleType,
    Type,
    UnitaryFlags,
    unify,
)

if TYPE_CHECKING:
    from guppylang_internals.checker.protocol_checker import ImplProof
    from guppylang_internals.tys.subst import Subst


@dataclass(frozen=True)
class FunctionTypeDef(TypeDef, CompiledDef):
    """Type definition associated with the builtin `Function` type.

    Any impls on functions can be registered with this definition.
    """

    name: Literal["Function"] = field(default="Function", init=False)

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> FunctionType:
        # Function types are constructed using special logic in the type parser
        raise InternalGuppyError(
            "Tried to construct `Function` type via `check_instantiate`"
        )


@dataclass(frozen=True)
class SelfTypeDef(TypeDef, CompiledDef):
    """Type definition associated with the `Self` type on methods.

    During type parsing, we make sure that this type is replaced with the concrete type
    the method is attached to. Thus, we should never have instances of this type around.

    In other words, this definition is only a marker so that type parsing doesn't have
    to rely on matching against the string "Self". By making `Self` a definition, we can
    use the existing identifier tracking system and also handle users shadowing the
    `Self` binder or assigning `Self` to some other name.
    """

    name: Literal["Self"] = field(default="Self", init=False)

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> FunctionType:
        raise InternalGuppyError("Tried to instantiate abstract `Self` type`")


@dataclass(frozen=True)
class _TupleTypeDef(TypeDef, CompiledDef):
    """Type definition associated with the builtin `tuple` type.

    Any impls on tuples can be registered with this definition.
    """

    name: Literal["tuple"] = field(default="tuple", init=False)

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> TupleType:
        # We accept any number of arguments. If users just write `tuple`, we give them
        # the empty tuple type. We just have to make sure that the args are of kind type
        args = [
            # TODO: Better error location
            TypeParam(0, f"T{i}", must_be_copyable=False, must_be_droppable=False)
            .check_arg(arg, loc)[0]
            .ty
            for i, arg in enumerate(args)
        ]
        return TupleType(args)


@dataclass(frozen=True)
class _NoneTypeDef(TypeDef, CompiledDef):
    """Type definition associated with the builtin `None` type.

    Any impls on None can be registered with this definition.
    """

    name: Literal["None"] = field(default="None", init=False)

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> NoneType:
        if args:
            raise GuppyError(WrongNumberOfTypeArgsError(loc, 0, len(args), "None"))
        return NoneType()


@dataclass(frozen=True)
class _NumericTypeDef(TypeDef, CompiledDef):
    """Type definition associated with the builtin numeric types.

    Any impls on numerics can be registered with these definitions.
    """

    ty: NumericType

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> NumericType:
        if args:
            raise GuppyError(WrongNumberOfTypeArgsError(loc, 0, len(args), self.name))
        return self.ty


class WasmModuleTypeDef(OpaqueTypeDef):
    wasm_file: str
    wasm_platform: WasmPlatform

    def __init__(
        self,
        id: DefId,
        name: str,
        defined_at: ast.AST | None,
        wasm_file: str,
        wasm_platform: WasmPlatform,
    ) -> None:
        super().__init__(id, name, defined_at, [], True, True, self.to_hugr)
        self.wasm_file = wasm_file
        self.wasm_platform = wasm_platform

    def to_hugr(
        self, args: Sequence[TypeArg | ConstArg], ctx: ToHugrContext
    ) -> ht.Type:
        assert args == []
        ty = WASM_EXTENSION.get_type("context")
        return ty.instantiate([])


@dataclass(frozen=True)
class _ListTypeDef(OpaqueTypeDef, CompiledDef):
    """Type definition associated with the builtin `list` type.

    We have a custom definition to disable usage of lists unless experimental features
    are enabled.
    """

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> OpaqueType:
        check_lists_enabled(loc)
        return super().check_instantiate(args, loc)


@dataclass(frozen=True)
class CallableProtocolDef(CheckedProtocolDef):
    """Protocol definition associated with the builtin `Callable` protocol."""

    name: Literal["Callable"] = field(default="Callable", init=False)
    params: Sequence[Parameter] = ()
    member_defs: Mapping[str, DefId] = field(default_factory=dict)

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> ProtocolInst:
        # Callable instances are constructed using special logic in the type parser
        raise InternalGuppyError(
            "Tried to build `Callable` type via `check_instantiate`"
        )


@dataclass(frozen=True, init=False)
class CallableProtocolInst(ProtocolInst):
    """Protocol instance associated with the builtin `Callable` protocol."""

    sig: FunctionType = field(hash=False)

    def __init__(self, sig: FunctionType):
        assert not sig.parametrized
        type_args = (*(TypeArg(inp.ty) for inp in sig.inputs), TypeArg(sig.output))
        super().__init__(type_args, callable_protocol_def.id)
        object.__setattr__(self, "sig", sig)

    def transform(self, transformer: Transformer) -> "CallableProtocolInst":
        sig = self.sig.transform(transformer)
        assert isinstance(sig, FunctionType)
        return CallableProtocolInst(sig)

    def check_implemented_by(
        self, ty: "Type", loc: ToSpan | None
    ) -> "tuple[ImplProof, Subst]":
        from guppylang_internals.checker.protocol_checker import (
            AssumptionImplProof,
            ConcreteImplProof,
        )

        if isinstance(ty, FunctionDefType):
            ty = ty.sig

        if isinstance(ty, FunctionType | FunctionDefType):
            assert not ty.parametrized
            sig = ty if isinstance(ty, FunctionType) else ty.sig
            subst = unify(self.sig, sig, {})
            if subst is not None:
                return ConcreteImplProof(
                    self.transform(Substituter(subst)), ty, {}
                ), subst

        elif isinstance(ty, BoundTypeVar):
            for protocol in ty.implements:
                if isinstance(protocol, CallableProtocolInst):
                    subst = unify(self.sig, protocol.sig, {})
                    if subst is not None:
                        return AssumptionImplProof(self, ty), subst

        raise GuppyError(DoesntImplementProtocol(loc, str(ty), str(self)))

    def __str__(self) -> str:
        inputs = ", ".join(str(inp.ty) for inp in self.sig.inputs)
        return f"Callable[[{inputs}], {self.sig.output}]"


@dataclass(frozen=True)
class ModifiableFunctionProtocolDef(CheckedProtocolDef):
    """Protocol definition associated with the builtin `Unitary`, `Controllable`, and
    Daggaerable` protocols.
    """

    name: str
    flags: UnitaryFlags

    def __init__(
        self,
        id: DefId,
        flags: UnitaryFlags,
        defined_at: ast.ClassDef | None,
    ) -> None:
        super().__init__(
            id, flags.callable_name(), defined_at, params=(), member_defs={}
        )
        object.__setattr__(self, "flags", flags)

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> ProtocolInst:
        # Modifiable function instances are constructed using special logic in the type
        # parser
        raise InternalGuppyError(
            f"Tried to build `{self.name}` type via `check_instantiate`"
        )


@dataclass(frozen=True, init=False)
class ModifiableFunctionProtocolInst(ProtocolInst):
    """Protocol instance associated with the builtin `Unitary`, `Controllable`, and
    `Daggaerable` protocols.
    """

    sig: FunctionType = field(hash=False)

    def __init__(self, sig: FunctionType):
        assert not sig.parametrized
        type_args = (*(TypeArg(inp.ty) for inp in sig.inputs), TypeArg(sig.output))
        super().__init__(type_args, callable_protocol_def.id)
        object.__setattr__(self, "sig", sig)

    def transform(self, transformer: Transformer) -> "ModifiableFunctionProtocolInst":
        sig = self.sig.transform(transformer)
        assert isinstance(sig, FunctionType)
        return ModifiableFunctionProtocolInst(sig)

    def check_implemented_by(
        self, ty: "Type", loc: ToSpan | None
    ) -> "tuple[ImplProof, Subst]":
        from guppylang_internals.checker.protocol_checker import (
            AssumptionImplProof,
            ConcreteImplProof,
        )

        err = DoesntImplementProtocol(loc, str(ty), str(self))
        if isinstance(ty, FunctionDefType):
            assert not ty.sig.parametrized
            subst = unify(self.sig, ty.sig, {})
            if subst is None:
                raise GuppyError(err)
            if self.sig.unitary_flags not in ty.sig.unitary_flags:
                hint = UnitaryFlagMismatchHint(
                    None, self.sig.unitary_flags, ty.sig.unitary_flags, ty.defn.name
                )
                err.add_sub_diagnostic(hint)
                raise GuppyError(err)
            return ConcreteImplProof(self.transform(Substituter(subst)), ty, {}), subst

        elif isinstance(ty, BoundTypeVar):
            for protocol in ty.implements:
                if isinstance(protocol, CallableProtocolInst):
                    subst = unify(self.sig, protocol.sig, {})
                    if subst is not None:
                        return AssumptionImplProof(self, ty), subst

        elif isinstance(ty, FunctionType):
            err.add_sub_diagnostic(FunctionPointerNotModifiableHint(None))

        raise GuppyError(err)

    def __str__(self) -> str:
        inputs = ", ".join(str(inp.ty) for inp in self.sig.inputs)
        name = self.sig.unitary_flags.callable_name()
        return f"{name}[[{inputs}], {self.sig.output}]"


def _list_to_hugr(args: Sequence[Argument], ctx: ToHugrContext) -> ht.Type:
    # Type checker ensures that we get a single arg of kind type
    [arg] = args
    assert isinstance(arg, TypeArg)
    # Linear elements are turned into an optional to enable unsafe indexing.
    # See `ListGetitemCompiler` for details.
    elem_ty = ht.Option(arg.ty.to_hugr(ctx)) if arg.ty.linear else arg.ty.to_hugr(ctx)
    return hugr.std.collections.list.List(elem_ty)


def _array_to_hugr(args: Sequence[Argument], ctx: ToHugrContext) -> ht.Type:
    # Type checker ensures that we get a two args
    [ty_arg, len_arg] = args
    assert isinstance(ty_arg, TypeArg)
    assert isinstance(len_arg, ConstArg)

    elem_ty = ty_arg.ty.to_hugr(ctx)
    hugr_arg = len_arg.to_hugr(ctx)

    return hugr.std.collections.borrow_array.BorrowArray(elem_ty, hugr_arg)


def _frozenarray_to_hugr(args: Sequence[Argument], ctx: ToHugrContext) -> ht.Type:
    # Type checker ensures that we get a two args
    [ty_arg, len_arg] = args
    assert isinstance(ty_arg, TypeArg)
    assert isinstance(len_arg, ConstArg)
    return hugr.std.collections.static_array.StaticArray(ty_arg.ty.to_hugr(ctx))


def _sized_iter_to_hugr(args: Sequence[Argument], ctx: ToHugrContext) -> ht.Type:
    [ty_arg, len_arg] = args
    assert isinstance(ty_arg, TypeArg)
    assert isinstance(len_arg, ConstArg)
    return ty_arg.ty.to_hugr(ctx)


def _option_to_hugr(args: Sequence[Argument], ctx: ToHugrContext) -> ht.Type:
    [arg] = args
    assert isinstance(arg, TypeArg)
    return ht.Option(arg.ty.to_hugr(ctx))


function_type_def = FunctionTypeDef(DefId.fresh(), None, None)
function_def_type_def = FunctionTypeDef(DefId.fresh(), None, None)
unitary_type_def = ModifiableFunctionProtocolDef(
    DefId.fresh(), UnitaryFlags.Unitary, None
)
daggerable_type_def = ModifiableFunctionProtocolDef(
    DefId.fresh(), UnitaryFlags.Dagger, None
)
controllable_type_def = ModifiableFunctionProtocolDef(
    DefId.fresh(), UnitaryFlags.Control, None
)
self_type_def = SelfTypeDef(DefId.fresh(), None, [])
tuple_type_def = _TupleTypeDef(DefId.fresh(), None, None)
none_type_def = _NoneTypeDef(DefId.fresh(), None, [])
bool_type_def = OpaqueTypeDef(
    id=DefId.fresh(),
    name="bool",
    defined_at=None,
    params=[],
    never_copyable=False,
    never_droppable=False,
    to_hugr=lambda args, ctx: ht.Bool,
)
nat_type_def = _NumericTypeDef(
    DefId.fresh(), "nat", None, [], NumericType(NumericType.Kind.Nat)
)
int_type_def = _NumericTypeDef(
    DefId.fresh(), "int", None, [], NumericType(NumericType.Kind.Int)
)
float_type_def = _NumericTypeDef(
    DefId.fresh(), "float", None, [], NumericType(NumericType.Kind.Float)
)
string_type_def = OpaqueTypeDef(
    id=DefId.fresh(),
    name="str",
    defined_at=None,
    params=[],
    never_copyable=False,
    never_droppable=False,
    to_hugr=lambda args, ctx: hugr.std.PRELUDE.get_type("string").instantiate([]),
)
list_type_def = _ListTypeDef(
    id=DefId.fresh(),
    name="list",
    defined_at=None,
    params=[TypeParam(0, "T", must_be_copyable=False, must_be_droppable=False)],
    never_copyable=False,
    never_droppable=False,
    to_hugr=_list_to_hugr,
)
array_type_def = OpaqueTypeDef(
    id=DefId.fresh(),
    name="array",
    defined_at=None,
    params=[
        TypeParam(0, "T", must_be_copyable=False, must_be_droppable=False),
        ConstParam(1, "n", NumericType(NumericType.Kind.Nat)),
    ],
    never_copyable=True,
    never_droppable=False,
    to_hugr=_array_to_hugr,
)
frozenarray_type_def = OpaqueTypeDef(
    id=DefId.fresh(),
    name="frozenarray",
    defined_at=None,
    params=[
        TypeParam(0, "T", must_be_copyable=True, must_be_droppable=True),
        ConstParam(1, "n", NumericType(NumericType.Kind.Nat)),
    ],
    never_copyable=False,
    never_droppable=False,
    to_hugr=_frozenarray_to_hugr,
)
sized_iter_type_def = OpaqueTypeDef(
    id=DefId.fresh(),
    name="SizedIter",
    defined_at=None,
    params=[
        TypeParam(0, "T", must_be_copyable=False, must_be_droppable=False),
        ConstParam(1, "n", NumericType(NumericType.Kind.Nat)),
    ],
    never_copyable=False,
    never_droppable=False,
    to_hugr=_sized_iter_to_hugr,
)
option_type_def = OpaqueTypeDef(
    id=DefId.fresh(),
    name="Option",
    defined_at=None,
    params=[TypeParam(0, "T", must_be_copyable=False, must_be_droppable=False)],
    never_copyable=False,
    never_droppable=False,
    to_hugr=_option_to_hugr,
)
callable_protocol_def = CallableProtocolDef(DefId.fresh(), defined_at=None)


def bool_type() -> OpaqueType:
    return OpaqueType([], bool_type_def)


def nat_type() -> NumericType:
    return NumericType(NumericType.Kind.Nat)


def int_type() -> NumericType:
    return NumericType(NumericType.Kind.Int)


def float_type() -> NumericType:
    return NumericType(NumericType.Kind.Float)


def string_type() -> OpaqueType:
    return OpaqueType([], string_type_def)


def list_type(element_ty: Type) -> OpaqueType:
    return OpaqueType([TypeArg(element_ty)], list_type_def)


def array_type(element_ty: Type, length: int | Const) -> OpaqueType:
    if isinstance(length, int):
        length = ConstValue(nat_type(), length)
    return OpaqueType([TypeArg(element_ty), ConstArg(length)], array_type_def)


def frozenarray_type(element_ty: Type, length: int | Const) -> OpaqueType:
    if isinstance(length, int):
        length = ConstValue(nat_type(), length)
    return OpaqueType([TypeArg(element_ty), ConstArg(length)], frozenarray_type_def)


def sized_iter_type(iter_type: Type, size: int | Const) -> OpaqueType:
    if isinstance(size, int):
        size = ConstValue(nat_type(), size)
    return OpaqueType([TypeArg(iter_type), ConstArg(size)], sized_iter_type_def)


def option_type(element_ty: Type) -> OpaqueType:
    return OpaqueType([TypeArg(element_ty)], option_type_def)


def is_bool_type(ty: Type) -> bool:
    return isinstance(ty, OpaqueType) and ty.defn == bool_type_def


def is_string_type(ty: Type) -> bool:
    return isinstance(ty, OpaqueType) and ty.defn == string_type_def


def is_list_type(ty: Type) -> bool:
    return isinstance(ty, OpaqueType) and ty.defn == list_type_def


def is_array_type(ty: Type) -> TypeGuard[OpaqueType]:
    return isinstance(ty, OpaqueType) and ty.defn == array_type_def


def is_frozenarray_type(ty: Type) -> TypeGuard[OpaqueType]:
    return isinstance(ty, OpaqueType) and ty.defn == frozenarray_type_def


def is_sized_iter_type(ty: Type) -> TypeGuard[OpaqueType]:
    return isinstance(ty, OpaqueType) and ty.defn == sized_iter_type_def


def wasm_module_name(ty: Type) -> str | None:
    if isinstance(ty, OpaqueType) and isinstance(ty.defn, WasmModuleTypeDef):
        return ty.defn.wasm_file
    return None


def get_element_type(ty: Type) -> Type:
    assert isinstance(ty, OpaqueType)
    assert ty.defn in (
        list_type_def,
        array_type_def,
        frozenarray_type_def,
        option_type_def,
    )
    (arg, *_) = ty.args
    assert isinstance(arg, TypeArg)
    return arg.ty


def get_array_length(ty: Type) -> Const:
    assert isinstance(ty, OpaqueType)
    assert ty.defn == array_type_def
    [_, length_arg] = ty.args
    assert isinstance(length_arg, ConstArg)
    return length_arg.const


def get_iter_size(ty: Type) -> Const:
    assert isinstance(ty, OpaqueType)
    assert ty.defn == sized_iter_type_def
    match ty.args:
        case [_, ConstArg(const)]:
            return const
        case _:
            raise InternalGuppyError("Unexpected type args")
