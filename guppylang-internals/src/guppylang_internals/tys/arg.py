from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypeAlias

from hugr import tys as ht

from guppylang_internals.error import InternalGuppyError
from guppylang_internals.tys.common import (
    ToHugr,
    ToHugrContext,
    Transformable,
    Transformer,
    Visitor,
)
from guppylang_internals.tys.const import (
    BoundConstVar,
    Const,
    ConstValue,
    ExistentialConstVar,
)
from guppylang_internals.tys.var import BoundVar, ExistentialVar

if TYPE_CHECKING:
    from guppylang_internals.tys.ty import Type


# We define the `Argument` type as a union of all `ArgumentBase` subclasses defined
# below. This models an algebraic data type and enables exhaustiveness checking in
# pattern matches etc.
# Note that this might become obsolete in case the `@sealed` decorator is added:
#  * https://peps.python.org/pep-0622/#sealed-classes-as-algebraic-data-types
#  * https://github.com/johnthagen/sealed-typing-pep
Argument: TypeAlias = "TypeArg | ConstArg"


@dataclass(frozen=True)
class ArgumentBase(ToHugr[ht.TypeArg], Transformable["Argument"], ABC):
    """Abstract base class for arguments of parametrized types.

    For example, in the type `array[int, 42]` we have two arguments `int` and `42`.
    """

    @property
    @abstractmethod
    def unsolved_vars(self) -> set[ExistentialVar]:
        """The existential type variables contained in this argument."""

    @property
    @abstractmethod
    def bound_vars(self) -> set[BoundVar]:
        """The bound type variables contained in this argument."""


@dataclass(frozen=True)
class TypeArg(ArgumentBase):
    """Argument that can be instantiated for a `TypeParameter`."""

    # The type to instantiate
    ty: "Type" = field(hash=False)  # Types are not hashable

    @property
    def unsolved_vars(self) -> set[ExistentialVar]:
        """The existential type variables contained in this argument."""
        return self.ty.unsolved_vars

    @property
    def bound_vars(self) -> set[BoundVar]:
        """The bound type variables contained in this type."""
        return self.ty.bound_vars

    def to_hugr(self, ctx: ToHugrContext) -> ht.TypeTypeArg:
        """Computes the Hugr representation of the argument."""
        ty: ht.Type = self.ty.to_hugr(ctx)
        return ty.type_arg()

    def visit(self, visitor: Visitor) -> None:
        """Accepts a visitor on this argument."""
        if not visitor.visit(self):
            self.ty.visit(visitor)

    def transform(self, transformer: Transformer) -> Argument:
        """Accepts a transformer on this argument."""
        return transformer.transform(self) or TypeArg(self.ty.transform(transformer))


@dataclass(frozen=True)
class ConstArg(ArgumentBase):
    """Argument that can be substituted for a `ConstParam`."""

    const: Const

    @property
    def unsolved_vars(self) -> set[ExistentialVar]:
        """The existential const variables contained in this argument."""
        return self.const.unsolved_vars

    @property
    def bound_vars(self) -> set[BoundVar]:
        """The bound type variables contained in this argument."""
        return self.const.bound_vars

    def to_hugr(self, ctx: ToHugrContext) -> ht.TypeArg:
        """Computes the Hugr representation of this argument."""
        from guppylang_internals.tys.ty import NumericType

        match self.const:
            case ConstValue(value=v, ty=NumericType(kind=NumericType.Kind.Nat)):
                assert isinstance(v, int)
                return ht.BoundedNatArg(n=v)
            case BoundConstVar() as var:
                return ctx.const_var_to_hugr(var)
            case ConstValue():
                raise InternalGuppyError(
                    "Tried to convert non-nat const type argument to Hugr. This should "
                    "have been monomorphized away."
                )
            case ExistentialConstVar():
                raise InternalGuppyError(
                    "Tried to convert unsolved constant variable to Hugr"
                )

    def visit(self, visitor: Visitor) -> None:
        """Accepts a visitor on this argument."""
        visitor.visit(self)

    def transform(self, transformer: Transformer) -> Argument:
        """Accepts a transformer on this argument."""
        return transformer.transform(self) or ConstArg(
            self.const.transform(transformer)
        )
