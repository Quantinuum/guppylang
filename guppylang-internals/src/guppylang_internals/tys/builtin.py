import ast
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal, TypeGuard

import hugr.std
import hugr.std.collections.array
import hugr.std.collections.list
from hugr import tys as ht

from guppylang_internals.ast_util import AstNode
from guppylang_internals.definition.common import CompiledDef, DefId
from guppylang_internals.definition.ty import OpaqueTypeDef, TypeDef
from guppylang_internals.error import GuppyError, InternalGuppyError
from guppylang_internals.experimental import check_lists_enabled
from guppylang_internals.std._internal.compiler.tket_bool import OpaqueBool
from guppylang_internals.std._internal.compiler.tket_exts import WASM_EXTENSION
from guppylang_internals.tys.arg import Argument, ConstArg, TypeArg
from guppylang_internals.tys.common import ToHugrContext
from guppylang_internals.tys.const import Const, ConstValue
from guppylang_internals.tys.errors import WrongNumberOfTypeArgsError
from guppylang_internals.tys.param import ConstParam, TypeParam
from guppylang_internals.tys.ty import (
    FunctionType,
    NoneType,
    NumericType,
    OpaqueType,
    TupleType,
    Type,
)


@dataclass(frozen=True)
class CallableTypeDef(TypeDef, CompiledDef):
    """Type definition associated with the builtin `Callable` type.

    Any impls on functions can be registered with this definition.
    """

    name: Literal["Callable"] = field(default="Callable", init=False)

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> FunctionType:
        # Callable types are constructed using special logic in the type parser
        raise InternalGuppyError("Tried to `Callable` type via `check_instantiate`")


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
            .check_arg(arg, loc)
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

    def __init__(
        self,
        id: DefId,
        name: str,
        defined_at: ast.AST | None,
        wasm_file: str,
    ) -> None:
        super().__init__(id, name, defined_at, [], True, True, self.to_hugr)
        self.wasm_file = wasm_file

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


callable_type_def = CallableTypeDef(DefId.fresh(), None, None)
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
    to_hugr=lambda args, ctx: OpaqueBool,
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
