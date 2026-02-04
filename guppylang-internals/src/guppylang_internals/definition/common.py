import ast
import itertools
from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, TypeAlias

from hugr.build.dfg import DefinitionBuilder, OpVar

from guppylang_internals.diagnostic import Fatal
from guppylang_internals.span import SourceMap

if TYPE_CHECKING:
    from guppylang_internals.checker.core import Globals
    from guppylang_internals.compiler.core import (
        CompilerContext,
        PartiallyMonomorphizedArgs,
    )
    from guppylang_internals.tys.param import Parameter


RawDef: TypeAlias = "ParsableDef | ParsedDef"
ParsedDef: TypeAlias = "CheckableDef | CheckedDef"
CheckedDef: TypeAlias = "CompilableDef | MonomorphizableDef | CompiledDef"


@dataclass(frozen=True)
class DefId:
    """Unique identifier for definitions across modules.

    This id is persistent across all compilation stages. It can be used to identify a
    definition at any step in the compilation pipeline.

    Args:
        id: An integer uniquely identifying the definition.
        module: The module where the definition was defined.
    """

    id: int

    _ids: ClassVar[Iterator[int]] = itertools.count()

    @classmethod
    def fresh(cls) -> "DefId":
        return DefId(next(cls._ids))


@dataclass(frozen=True)
class Definition(ABC):
    """Abstract base class for user-defined objects on module-level.

    Each definition is identified by a globally unique id. Furthermore, we store the
    user-picked name for the defined object and an optional AST node for the definition
    location.

    Args:
        id: The unique definition identifier.
        name: The name of the definition.
        defined_at: The AST node where the definition was defined.
    """

    id: DefId
    name: str
    defined_at: ast.AST | None

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of this definition to be used in messages to the user.

        The returned text should fit into messages of the following form: "expected
        a function, but got {description of this definition} instead".
        """


class ParsableDef(Definition):
    """Abstract base class for raw definitions that still require parsing.

    For example, raw function definitions first need to parse their signature and check
    that all types are valid. The result of parsing should be a definition that is ready
    to be checked.

    Args:
        id: The unique definition identifier.
        name: The name of the definition.
        defined_at: The AST node where the definition was defined.
    """

    @abstractmethod
    def parse(self, globals: "Globals", sources: SourceMap) -> ParsedDef:
        """Performs parsing and validation, returning a definition that can be checked.

        The provided globals contain all other raw definitions that have been defined.
        """


class CheckableDef(Definition):
    """Abstract base class for definitions that still need to be checked.

    The result of checking should be a definition that is ready to be compiled to Hugr.

    Args:
        id: The unique definition identifier.
        name: The name of the definition.
        defined_at: The AST node where the definition was defined.
    """

    @abstractmethod
    def check(self, globals: "Globals") -> CheckedDef:
        """Type checks the definition.

        The provided globals contain all other parsed definitions that have been
        defined.

        Returns a checked version of the definition that can be compiled to Hugr.
        """


class CompilableDef(Definition):
    """Abstract base class for definitions that still need to be compiled to Hugr.

    The result of compilation should be a `CompiledDef` with a pointer to the Hugr node
    that was created for this definition.

    Args:
        id: The unique definition identifier.
        name: The name of the definition.
        defined_at: The AST node where the definition was defined.
    """

    @abstractmethod
    def compile_outer(
        self, module: DefinitionBuilder[OpVar], ctx: "CompilerContext"
    ) -> "CompiledDef":
        """Adds a Hugr node for the definition to the provided Hugr module.

        Note that is not required to fill in the contents of the node. At this point,
        we don't have access to the globals since they have not all been compiled yet.

        See `CompiledDef.compile_inner()` for the hook to compile the inside of the
        node. This two-step process enables things like mutual recursion.
        """


class MonomorphizableDef(Definition):
    """Abstract base class for definitions that require monomorphization when compiling
    to Hugr.

    Args:
        id: The unique definition identifier.
        name: The name of the definition.
        defined_at: The AST node where the definition was defined.
    """

    @property
    @abstractmethod
    def params(self) -> "Sequence[Parameter]":
        """Generic parameters of this definition."""

    @abstractmethod
    def monomorphize(
        self,
        module: DefinitionBuilder[OpVar],
        mono_args: "PartiallyMonomorphizedArgs",
        ctx: "CompilerContext",
        parent_ty: "RawDef | None" = None,
    ) -> "MonomorphizedDef":
        """Adds a Hugr node for the (partially) monomorphized definition to the provided
        Hugr module.

        See `MonomorphizedDef.compile_inner()` for the hook to compile the inside of the
        node. This two-step process enables things like mutual recursion.
        """


class CompiledDef(Definition):
    """Abstract base class for definitions that have been added to a Hugr.

    Args:
        id: The unique definition identifier.
        name: The name of the definition.
        defined_at: The AST node where the definition was defined.
    """

    def compile_inner(self, ctx: "CompilerContext") -> None:
        """Optional hook that is called to fill in the content of the Hugr node.

        Opposed to `CompilableDef.compile()`, we have access to all other compiled
        definitions here, which allows things like mutual recursion.
        """


@dataclass(frozen=True)
class MonomorphizedDef(CompiledDef):
    """Abstract base class for definitions that have been added to a Hugr and have been
    partially monomorphized.

    Args:
        id: The unique definition identifier.
        name: The name of the definition. This will be the same for all monomorphized
            variants of the definition.
        defined_at: The AST node where the original polymorphic definition was defined.
        mono_args: Partial monomorphization of the generic parameters.
    """

    mono_args: "PartiallyMonomorphizedArgs"


@dataclass(frozen=True)
class UnknownSourceError(Fatal):
    title: ClassVar[str] = "Cannot find source"
    message: ClassVar[str] = (
        "Unable to look up the source code for Python object `{obj}`"
    )
    obj: object
