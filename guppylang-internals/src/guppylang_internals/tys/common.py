from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeVar

from hugr import tys as ht

if TYPE_CHECKING:
    from guppylang_internals.tys.const import BoundConstVar
    from guppylang_internals.tys.param import Parameter
    from guppylang_internals.tys.ty import BoundTypeVar

T = TypeVar("T")


class ToHugrContext(Protocol):
    """Protocol for the context capabilities required to translate Guppy types into Hugr
    types.

    Currently, the only required capability is translating bound type and const
    variables into Hugr, taking into account partial monomorphization.
    """

    def type_var_to_hugr(self, var: "BoundTypeVar") -> ht.Type:
        """Compiles a bound Guppy type variable into a Hugr type.

        Should take care of performing partial monomorphization as specified in the
        current context.
        """

    def const_var_to_hugr(self, var: "BoundConstVar") -> ht.TypeArg:
        """Compiles a bound Guppy const variable into a Hugr type argument.

        Should take care of performing partial monomorphization as specified in the
        current context.
        """


@dataclass(frozen=True)
class QuantifiedToHugrContext(ToHugrContext):
    """Concrete implementation of a `ToHugrContext` that should be used when moving
    inside a quantifier.

    This prevents the outer context from touching variables that are bound by a tighter
    quantifier.
    """

    params: Sequence["Parameter"]

    def type_var_to_hugr(self, var: "BoundTypeVar") -> ht.Type:
        return ht.Variable(var.idx, var.hugr_bound)

    def const_var_to_hugr(self, var: "BoundConstVar") -> ht.TypeArg:
        return ht.VariableArg(var.idx, self.params[var.idx].to_hugr(self))


class ToHugr(ABC, Generic[T]):
    """Abstract base class for objects that have a Hugr representation."""

    @abstractmethod
    def to_hugr(self, ctx: ToHugrContext) -> T:
        """Computes the Hugr representation of the object."""


class Visitor(ABC):
    """Abstract base class for a type visitor that transforms types."""

    @abstractmethod
    def visit(self, arg: Any, /) -> bool:
        """This method is called for each visited type.

        Return `False` to continue the recursive descent.
        """


class Transformer(ABC):
    """Abstract base class for a type visitor that transforms types."""

    @abstractmethod
    def transform(self, arg: Any, /) -> Any | None:
        """Transforms the object.

        Return a transformed type or `None` to continue the recursive visit.
        """


class Visitable(ABC):
    """Abstract base class for objects that can be recursively visited."""

    @abstractmethod
    def visit(self, visitor: Visitor, /) -> None:
        """Accepts a visitor on the object.

        Implementors of this method should first invoke the visitor on the object
        itself. If the visitor doesn't handle the object, the visitor should be passed
        to all relevant members of the object.
        """


class Transformable(Visitable, ABC, Generic[T]):
    """Abstract base class for objects that can be recursively transformed."""

    @abstractmethod
    def transform(self, transformer: Transformer, /) -> T:
        """Accepts a transformer on the object.

        Implementors of this method should first invoke the transformer on the object
        itself. If the visitor doesn't handle the object, the visitor should be used to
        transform all relevant members of the object.
        """
