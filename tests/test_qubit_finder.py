from dataclasses import dataclass
from types import SimpleNamespace
from typing import cast

import pytest
from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.enum import EnumVariant
from guppylang_internals.definition.util import CheckedField
from guppylang_internals.error import InternalGuppyError
from guppylang_internals.tys.arg import ConstArg, TypeArg
from guppylang_internals.tys.builtin import array_type_def
from guppylang_internals.tys.const import ConstValue
from guppylang_internals.tys.qubit import QubitFinder, contain_qubit_ty, qubit_ty
from guppylang_internals.tys.ty import (
    BoundTypeVar,
    EnumType,
    ExistentialTypeVar,
    FuncInput,
    FunctionDefType,
    FunctionType,
    InputFlags,
    NestedFunctionDefType,
    NoneType,
    NumericType,
    OpaqueType,
    StructType,
    TupleType,
    Type,
    TypeBase,
)


def array_of(ty):
    return OpaqueType(
        [TypeArg(ty), ConstArg(ConstValue(NumericType(NumericType.Kind.Nat), 2))],
        array_type_def,
    )


def struct_of(ty):
    return StructType([], SimpleNamespace(fields=[CheckedField("field", ty)]))


def enum_of(ty):
    return EnumType(
        [],
        SimpleNamespace(
            variants={"Value": EnumVariant(0, "Value", [CheckedField("field", ty)])}
        ),
    )


@pytest.mark.parametrize(
    "ty",
    [
        NoneType(),
        NumericType(NumericType.Kind.Nat),
        BoundTypeVar("T", 0, True, True),
        ExistentialTypeVar("T", 0, True, True),
        FunctionDefType(DefId(0)),
        NestedFunctionDefType(DefId(0)),
        FunctionType([], NoneType()),
        TupleType([]),
        array_of(NoneType()),
        struct_of(NoneType()),
        enum_of(NoneType()),
    ],
)
def test_current_types_without_qubits(ty):
    assert not contain_qubit_ty(ty)


@pytest.mark.parametrize(
    "wrap",
    [
        lambda ty: ty,
        lambda ty: TupleType([NoneType(), ty]),
        array_of,
        struct_of,
        enum_of,
        lambda ty: FunctionType([FuncInput(ty, InputFlags.NoFlags)], NoneType()),
        lambda ty: FunctionType([], ty),
        lambda ty: FunctionDefType(DefId(0), [TypeArg(ty)]),
        lambda ty: NestedFunctionDefType(DefId(0), [TypeArg(ty)]),
        lambda ty: array_of(struct_of(enum_of(TupleType([ty])))),
    ],
)
def test_nested_qubits(wrap):
    assert contain_qubit_ty(wrap(qubit_ty()))


@dataclass(frozen=True)
class FutureType(TypeBase):
    copyable = True
    droppable = True

    def cast(self):
        return cast("Type", self)

    def to_hugr(self, ctx):
        raise NotImplementedError

    def visit(self, visitor):
        visitor.visit(self)

    def transform(self, transformer):
        return transformer.transform(self) or self


def test_unhandled_future_type_fails():
    with pytest.raises(AssertionError):
        contain_qubit_ty(cast("Type", FutureType()))


def test_unhandled_visitor_node_fails():
    with pytest.raises(InternalGuppyError, match="Unhandled node in QubitFinder"):
        QubitFinder().visit(object())
