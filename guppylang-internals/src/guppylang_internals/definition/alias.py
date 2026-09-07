import ast
from collections.abc import Sequence
from dataclasses import dataclass, field

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.core import Globals
from guppylang_internals.definition.common import (
    CheckableDef,
    CompiledDef,
    ParsableDef,
)
from guppylang_internals.definition.parameter import ParamDef, RawConstVarDef
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.definition.util import check_not_recursive
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.error import InternalGuppyError
from guppylang_internals.span import SourceMap
from guppylang_internals.tys.arg import Argument
from guppylang_internals.tys.param import Parameter, check_all_args
from guppylang_internals.tys.parsing import TypeParsingCtx, type_from_ast
from guppylang_internals.tys.subst import Instantiator
from guppylang_internals.tys.ty import Type


@dataclass(frozen=True)
class RawTypeAliasDef(TypeDef, ParsableDef):
    """A raw type alias definition that has not been parsed yet."""

    type_ast: ast.expr
    explicit_params: Sequence[ParamDef] | None = None
    params: None = field(default=None, init=False)
    description: str = field(default="type alias", init=False)

    def parse(self, globals: Globals, sources: SourceMap) -> "ParsedTypeAliasDef":
        return ParsedTypeAliasDef(
            self.id,
            self.name,
            self.defined_at,
            self.explicit_params,
            self.type_ast,
        )

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        raise InternalGuppyError("Tried to instantiate raw type alias definition")


def _resolve_param(defn: ParamDef, idx: int, globals: Globals) -> Parameter:
    """Convert a parameter definition to a positional :class:`Parameter`.

    ``const_var`` definitions arrive unparsed (their type is still a raw AST), so we
    parse them here, where the ``globals`` needed to resolve the type are available.
    """
    if isinstance(defn, RawConstVarDef):
        defn = defn.parse(globals, DEF_STORE.sources)
    return defn.to_param(idx)


@dataclass(frozen=True)
class ParsedTypeAliasDef(TypeDef, CheckableDef):
    """A type alias definition whose target type has not been checked yet."""

    param_defs: Sequence[ParamDef] | None
    type_ast: ast.expr
    params: None = field(default=None, init=False)
    description: str = field(default="type alias", init=False)

    def check(self, globals: Globals) -> "CheckedTypeAliasDef":
        if self.param_defs is not None:
            # Explicit params: resolve each definition to a parameter (parsing
            # `const_var` types now that globals are available) and pre-load them
            # into the context so that variables in the body bind to these params
            # in order.
            resolved = [
                _resolve_param(p, i, globals) for i, p in enumerate(self.param_defs)
            ]
            ctx = TypeParsingCtx(
                globals, param_var_mapping={p.name: p for p in resolved}
            )
            check_not_recursive(self, ctx)
            ty = type_from_ast(self.type_ast, ctx)
            params = tuple(resolved)
        else:
            # Implicit: collect free type vars from the body in order of appearance.
            ctx = TypeParsingCtx(globals, allow_free_vars=True)
            check_not_recursive(self, ctx)
            ty = type_from_ast(self.type_ast, ctx)
            params = tuple(ctx.param_var_mapping.values())
        return CheckedTypeAliasDef(
            self.id,
            self.name,
            self.defined_at,
            params,
            ty,
        )

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        globals = Globals(DEF_STORE.frames[self.id])
        checked_def = self.check(globals)
        return checked_def.check_instantiate(args, loc)


@dataclass(frozen=True)
class CheckedTypeAliasDef(TypeDef, CompiledDef):
    """A fully checked type alias definition."""

    params: Sequence[Parameter]
    ty: Type
    description: str = field(default="type alias", init=False)

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        check_all_args(self.params, args, self.name, loc)
        return self.ty.transform(Instantiator(args))
