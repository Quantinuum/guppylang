from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeAlias

from guppylang_internals.error import InternalGuppyError
from guppylang_internals.tys.common import Transformable, Transformer, Visitor
from guppylang_internals.tys.var import BoundVar, ExistentialVar

if TYPE_CHECKING:
    from guppylang_internals.tys.arg import ConstArg
    from guppylang_internals.tys.subst import Subst
    from guppylang_internals.tys.ty import Type


@dataclass(frozen=True)
class ConstBase(Transformable["Const"], ABC):
    """Abstract base class for constants arguments in the type system.

    In principle, we can allow constants of any type representable in the type system.
    For now, we will only support basic consts like `int` or `bool`, but in the future
    we could have struct constants etc.
    """

    ty: "Type" = field(hash=False)  # Types are not hashable

    def __post_init__(self) -> None:
        if self.ty.unsolved_vars:
            raise InternalGuppyError("Attempted to create constant with unsolved type")

    @abstractmethod
    def cast(self) -> "Const":
        """Casts an implementor of `ConstBase` into a `Const`.

        This enforces that all implementors of `ConstBase` can be embedded into the
        `Const` union type.
        """

    @property
    def unsolved_vars(self) -> set[ExistentialVar]:
        """The existential type variables contained in this constant."""
        return set()

    @property
    def bound_vars(self) -> set[BoundVar]:
        """The bound type variables contained in this constant."""
        return self.ty.bound_vars

    def __str__(self) -> str:
        from guppylang_internals.tys.printing import TypePrinter

        return TypePrinter().visit(self.cast())

    def visit(self, visitor: Visitor) -> None:
        """Accepts a visitor on this constant."""
        visitor.visit(self)

    def to_arg(self) -> "ConstArg":
        """Wraps this constant into a type argument."""
        from guppylang_internals.tys.arg import ConstArg

        return ConstArg(self.cast())

    def substitute(self, subst: "Subst") -> "Const":
        """Substitutes existential variables in this constant."""
        from guppylang_internals.tys.subst import Substituter

        return self.transform(Substituter(subst))


@dataclass(frozen=True)
class ConstValue(ConstBase):
    """A constant value in the type system.

    For example, in the type `array[int, 5]` the second argument is a `ConstArg`  that
    contains a `ConstValue(5)`.
    """

    # TODO: We will need a proper Guppy representation of this in the future
    value: Any

    def cast(self) -> "Const":
        """Casts an implementor of `ConstBase` into a `Const`."""
        return self

    def transform(self, transformer: Transformer, /) -> "Const":
        """Accepts a transformer on this constant."""
        return transformer.transform(self) or self


@dataclass(frozen=True)
class BoundConstVar(BoundVar, ConstBase):
    """Bound variable referencing a `ConstParam`.

    For example, in the function type `forall n: int. array[float, n] -> array[int, n]`,
    we represent the int argument to `array` as a `ConstArg` containing a
    `BoundConstVar(idx=0)`.
    """

    @property
    def bound_vars(self) -> set[BoundVar]:
        """The bound type variables contained in this constant."""
        return {self} | self.ty.bound_vars

    def cast(self) -> "Const":
        """Casts an implementor of `ConstBase` into a `Const`."""
        return self

    def transform(self, transformer: Transformer, /) -> "Const":
        """Accepts a transformer on this constant."""
        return transformer.transform(self) or BoundConstVar(
            transformer.transform(self.ty) or self.ty, self.display_name, self.idx
        )


@dataclass(frozen=True)
class ExistentialConstVar(ExistentialVar, ConstBase):
    """Existential constant variable.

    During type checking we try to solve all existential constant variables and
    substitute them with concrete constants.
    """

    @classmethod
    def fresh(cls, display_name: str, ty: "Type") -> "ExistentialConstVar":
        return ExistentialConstVar(ty, display_name, next(cls._fresh_id))

    @property
    def unsolved_vars(self) -> set[ExistentialVar]:
        """The existential type variables contained in this constant."""
        return {self}

    def cast(self) -> "Const":
        """Casts an implementor of `ConstBase` into a `Const`."""
        return self

    def transform(self, transformer: Transformer, /) -> "Const":
        """Accepts a transformer on this constant."""
        return transformer.transform(self) or ExistentialConstVar(
            transformer.transform(self.ty) or self.ty, self.display_name, self.id
        )


Const: TypeAlias = ConstValue | BoundConstVar | ExistentialConstVar
