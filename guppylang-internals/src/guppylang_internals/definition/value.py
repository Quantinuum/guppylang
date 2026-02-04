import ast
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, NamedTuple

from hugr import Node, Wire

from guppylang_internals.ast_util import AstNode
from guppylang_internals.definition.common import CompiledDef, Definition
from guppylang_internals.tys.subst import Inst, Subst
from guppylang_internals.tys.ty import FunctionType, Type

if TYPE_CHECKING:
    from guppylang_internals.checker.core import Context
    from guppylang_internals.compiler.core import CompilerContext, DFContainer


@dataclass(frozen=True)
class ValueDef(Definition):
    """Abstract base class for definitions that represent values."""

    ty: Type

    description: str = field(default="value", init=False)


@dataclass(frozen=True)
class CompiledValueDef(ValueDef, CompiledDef):
    """Abstract base class for compiled definitions that represent values."""

    @abstractmethod
    def load(self, dfg: "DFContainer", ctx: "CompilerContext", node: AstNode) -> Wire:
        """Loads the defined value into a local Hugr dataflow graph."""


@dataclass(frozen=True)
class CallableDef(ValueDef):
    """Abstract base class for definitions that represent functions."""

    ty: FunctionType

    @abstractmethod
    def check_call(
        self, args: list[ast.expr], ty: Type, node: AstNode, ctx: "Context"
    ) -> tuple[ast.expr, Subst]:
        """Checks the return type of a function call against a given type."""

    @abstractmethod
    def synthesize_call(
        self, args: list[ast.expr], node: AstNode, ctx: "Context"
    ) -> tuple[ast.expr, Type]:
        """Synthesizes the return type of a function call."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("Guppy functions can only be called in a Guppy context")


class CompiledCallableDef(CallableDef, CompiledValueDef):  # type: ignore[misc, unused-ignore]
    """Abstract base class a global module-level function."""

    ty: FunctionType

    @abstractmethod
    def compile_call(
        self,
        args: list[Wire],
        type_args: Inst,
        dfg: "DFContainer",
        ctx: "CompilerContext",
        node: AstNode,
    ) -> "CallReturnWires":
        """Compiles a call to the function.

        Returns the outputs of the call together with any borrowed arguments that are
        passed through the function.
        """

    @abstractmethod
    def load_with_args(
        self,
        type_args: Inst,
        dfg: "DFContainer",
        ctx: "CompilerContext",
        node: AstNode,
    ) -> Wire:
        """Loads the function into a local Hugr dataflow graph.

        Requires an instantiation for all function parameters.
        """

    def load(
        self, dfg: "DFContainer", globals: "CompilerContext", node: AstNode
    ) -> Wire:
        """Loads the defined value into a local Hugr dataflow graph."""
        return self.load_with_args([], dfg, globals, node)


class CallReturnWires(NamedTuple):
    """Output wires that are given back from a call.

    Contains the regular function returns together with any borrowed arguments that are
    passed through the function.
    """

    regular_returns: list[Wire]
    inout_returns: list[Wire]


class CompiledHugrNodeDef(Definition):
    """Abstract base class for definitions that are compiled into a single Hugr node."""

    @property
    @abstractmethod
    def hugr_node(self) -> Node:
        """The Hugr node this definition was compiled into."""
