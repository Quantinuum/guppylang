import functools
from typing import TYPE_CHECKING, Any, assert_never, cast

from guppylang_internals.error import InternalGuppyError
from guppylang_internals.tys.arg import ConstArg, TypeArg
from guppylang_internals.tys.common import Visitor
from guppylang_internals.tys.ty import (
    BoundTypeVar,
    EnumType,
    ExistentialTypeVar,
    FunctionDefType,
    FunctionType,
    NoneType,
    NumericType,
    OpaqueType,
    StructType,
    TupleType,
    Type,
    TypeBase,
)

if TYPE_CHECKING:
    from guppylang_internals.definition.ty import TypeDef


@functools.cache
def qubit_ty() -> Type:
    """Returns the qubit type. Beware that this function imports guppylang definitions,
    so, if called before the definitions are registered,
    it might result in circular imports.
    """
    from guppylang.defs import GuppyDefinition
    from guppylang.std.quantum import qubit

    assert isinstance(qubit, GuppyDefinition)
    qubit_ty = cast("TypeDef", qubit.wrapped).check_instantiate([])
    return qubit_ty


def is_qubit_ty(ty: Type) -> bool:
    """Checks if the given type is the qubit type.
    This function results in circular imports if called
    before qubit types are registered.
    """
    return ty == qubit_ty()


class QubitFinder(Visitor):
    """Type visitor that checks if a type contains the qubit type."""

    class FoundFlag(Exception):
        pass

    @functools.singledispatchmethod
    def visit(self, ty: Any) -> bool:
        raise InternalGuppyError(f"Unhandled node in QubitFinder: {type(ty).__name__}")

    @visit.register
    def _visit_Type(self, ty: TypeBase) -> bool:
        # Keep this match exhaustive over the closed Type union. New type variants
        # must explicitly decide how their contained types are searched.
        match ty.cast():
            case BoundTypeVar() | ExistentialTypeVar() | NumericType() | NoneType():
                pass
            case FunctionType() as func:
                for inp in func.inputs:
                    inp.ty.visit(self)
                func.output.visit(self)
            case FunctionDefType() as func_def:
                for arg in func_def.args:
                    self.visit(arg)
            case TupleType() as tup:
                for element in tup.element_types:
                    element.visit(self)
            case OpaqueType() as opaque:
                if is_qubit_ty(opaque):
                    raise self.FoundFlag
                for arg in opaque.args:
                    self.visit(arg)
            case StructType() as struct:
                for field in struct.fields:
                    field.ty.visit(self)
            case EnumType() as enum:
                for variant in enum.variants_as_list:
                    for field in variant.fields:
                        field.ty.visit(self)
            case unexpected:
                assert_never(unexpected)
        return True

    @visit.register
    def _visit_TypeArg(self, arg: TypeArg) -> bool:
        arg.ty.visit(self)
        return True

    @visit.register
    def _visit_ConstArg(self, arg: ConstArg) -> bool:
        # Preserve the existing traversal: do not descend into constant arguments.
        return True


def contain_qubit_ty(ty: Type) -> bool:
    """Checks if the given type contains the qubit type."""
    finder = QubitFinder()
    try:
        ty.visit(finder)
    except QubitFinder.FoundFlag:
        return True
    else:
        return False
