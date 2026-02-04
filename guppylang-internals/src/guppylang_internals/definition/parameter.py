import ast
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar

from guppylang_internals.checker.core import Globals
from guppylang_internals.definition.common import CompiledDef, Definition, ParsableDef
from guppylang_internals.diagnostic import Error
from guppylang_internals.error import GuppyError, InternalGuppyError
from guppylang_internals.span import SourceMap
from guppylang_internals.tys.param import ConstParam, Parameter, TypeParam
from guppylang_internals.tys.ty import Type


@dataclass(frozen=True)
class LinearConstVarError(Error):
    title: ClassVar[str] = "Invalid const variable"
    span_label: ClassVar[str] = (
        "Const variable `{name}` is not allowed have {thing} type `{ty}`"
    )
    name: str
    ty: Type

    @property
    def thing(self) -> str:
        return "non-copyable" if not self.ty.copyable else "non-droppable"


class ParamDef(Definition):
    """Abstract base class for type parameter definitions."""

    @abstractmethod
    def to_param(self, idx: int) -> Parameter:
        """Creates a parameter from this definition."""


@dataclass(frozen=True)
class TypeVarDef(ParamDef, CompiledDef):
    """A type variable definition."""

    copyable: bool
    droppable: bool

    description: str = field(default="type variable", init=False)

    def to_param(self, idx: int) -> TypeParam:
        """Creates a parameter from this definition."""
        return TypeParam(
            idx,
            self.name,
            must_be_copyable=self.copyable,
            must_be_droppable=self.droppable,
        )


@dataclass(frozen=True)
class RawConstVarDef(ParamDef, ParsableDef):
    """A constant variable definition whose type is not parsed yet."""

    type_ast: ast.expr
    description: str = field(default="const variable", init=False)

    def parse(self, globals: Globals, sources: SourceMap) -> "ConstVarDef":
        from guppylang_internals.tys.parsing import TypeParsingCtx, type_from_ast

        ty = type_from_ast(self.type_ast, TypeParsingCtx(globals))
        if not ty.copyable or not ty.droppable:
            raise GuppyError(LinearConstVarError(self.type_ast, self.name, ty))
        return ConstVarDef(self.id, self.name, self.defined_at, ty)

    def to_param(self, idx: int) -> Parameter:
        raise InternalGuppyError(
            "RawConstVarDef.to_param: Parameter conversion only possible after parsing"
        )


@dataclass(frozen=True)
class ConstVarDef(ParamDef, CompiledDef):
    """A constant variable definition."""

    ty: Type

    description: str = field(default="const variable", init=False)

    def to_param(self, idx: int) -> ConstParam:
        """Creates a parameter from this definition."""
        return ConstParam(idx, self.name, self.ty)
