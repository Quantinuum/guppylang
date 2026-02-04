import itertools
from abc import ABC
from collections.abc import Iterator
from dataclasses import dataclass
from typing import ClassVar

# Type of de Bruijn indices
DeBruijn = int

# Type of unique variable identifiers
UniqueId = int


@dataclass(frozen=True)
class Var(ABC):
    """Abstract base class for variables that occur in types.

    A variable can either occur as a type itself (see subclasses `BoundTypeVar` and
    `ExistentialTypeVar`) or as an argument to a parametrised type.
    """

    # Name that is used when showing the variable to the user
    display_name: str


@dataclass(frozen=True)
class BoundVar(Var, ABC):
    """Variable that is bound to a parameter of kind `Const`.

    Identified by a de Bruijn index.
    """

    idx: DeBruijn


@dataclass(frozen=True)
class ExistentialVar(Var, ABC):
    """Existential variable, referencing a parameter of kind `Const`.

    Identified by a globally unique id.

    During type checking we try to solve all existential variables and substitute
    them with concrete consts.
    """

    id: UniqueId

    # Generator of fresh unique ids
    _fresh_id: ClassVar[Iterator[UniqueId]] = itertools.count()
