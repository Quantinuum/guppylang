import functools
from typing import TYPE_CHECKING, Any, assert_never, cast

from guppylang_internals.error import InternalGuppyError
from guppylang_internals.tys.arg import Argument, ConstArg, TypeArg
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

    def visit(self, ty: Any) -> bool:
        node: Type | Argument
        if isinstance(ty, TypeBase):
            node = ty.cast()
        elif isinstance(ty, TypeArg | ConstArg):
            node = ty
        else:
            raise InternalGuppyError(
                f"Unhandled node in QubitFinder: {type(ty).__name__}"
            )

        # Keep this match exhaustive over types and arguments. New variants must
        # explicitly decide how their contained types are searched.
        match node:
            case BoundTypeVar() | ExistentialTypeVar() | NumericType() | NoneType():
                pass
            case FunctionType(inputs=inputs, output=output):
                for inp in inputs:
                    inp.ty.visit(self)
                output.visit(self)
            case FunctionDefType(args=args):
                for arg in args:
                    self.visit(arg)
            case TupleType(element_types=elements):
                for element in elements:
                    element.visit(self)
            case OpaqueType(args=args) as opaque:
                if is_qubit_ty(opaque):
                    raise self.FoundFlag
                for arg in args:
                    self.visit(arg)
            case StructType(fields=fields):
                for field in fields:
                    field.ty.visit(self)
            case EnumType(variants_as_list=variants):
                for variant in variants:
                    for field in variant.fields:
                        field.ty.visit(self)
            case TypeArg(ty=arg_ty):
                arg_ty.visit(self)
            case ConstArg():
                # Constant arguments do not contribute qubits to the enclosing type.
                pass
            case unexpected:
                assert_never(unexpected)
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
