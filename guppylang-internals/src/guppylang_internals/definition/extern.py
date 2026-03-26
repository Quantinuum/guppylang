import ast
from dataclasses import dataclass, field

from hugr import Node, Wire, val
from hugr.build.dfg import DefinitionBuilder, OpVar

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.core import Globals
from guppylang_internals.compiler.core import CompilerContext, DFContainer
from guppylang_internals.definition.common import CompilableDef, ParsableDef
from guppylang_internals.definition.value import (
    CompiledHugrNodeDef,
    CompiledValueDef,
    ValueDef,
)
from guppylang_internals.span import SourceMap
from guppylang_internals.tys.parsing import TypeParsingCtx, type_from_ast


@dataclass(frozen=True)
class RawExternDef(ParsableDef):
    """A raw extern symbol definition provided by the user."""

    symbol: str
    constant: bool
    type_ast: ast.expr

    description: str = field(default="extern", init=False)

    def parse(self, globals: Globals, sources: SourceMap) -> "ExternDef":
        """Parses and checks the user-provided signature of the function."""
        return ExternDef(
            self.id,
            self.name,
            self.defined_at,
            type_from_ast(self.type_ast, TypeParsingCtx(globals)),
            self.symbol,
            self.constant,
            self.type_ast,
        )


@dataclass(frozen=True)
class ExternDef(RawExternDef, ValueDef, CompilableDef):
    """An extern symbol definition."""

    def compile_outer(
        self, graph: DefinitionBuilder[OpVar], ctx: CompilerContext
    ) -> "CompiledExternDef":
        """Adds a Hugr constant node for the extern definition to the provided graph."""
        # The `typ` field must be serialized at this point, to ensure that the
        # `Extension` is serializable.
        custom_const = {
            "symbol": self.symbol,
            "typ": self.ty.to_hugr(ctx)._to_serial_root(),
            "constant": self.constant,
        }
        value = val.Extension(
            name="ConstExternalSymbol",
            typ=self.ty.to_hugr(ctx),
            val=custom_const,
        )
        const_node = graph.add_const(value)
        return CompiledExternDef(
            self.id,
            self.name,
            self.defined_at,
            self.ty,
            self.symbol,
            self.constant,
            self.type_ast,
            const_node,
        )


@dataclass(frozen=True)
class CompiledExternDef(ExternDef, CompiledValueDef, CompiledHugrNodeDef):
    """An extern symbol definition that has been compiled to a Hugr constant."""

    const_node: Node

    @property
    def hugr_node(self) -> Node:
        """The Hugr node this definition was compiled into."""
        return self.const_node

    def load(self, dfg: DFContainer, ctx: CompilerContext, node: AstNode) -> Wire:
        """Loads the extern value into a local Hugr dataflow graph."""
        return dfg.builder.load(self.const_node)
