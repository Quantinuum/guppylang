from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from guppylang_internals.definition.common import DefId
from guppylang_internals.error import RequiresMonomorphizationError
from guppylang_internals.tys.common import Transformable, Transformer, Visitor
from guppylang_internals.tys.var import BoundVar, ExistentialVar

if TYPE_CHECKING:
    from guppylang_internals.nodes import ComptimeExpr
    from guppylang_internals.tys.arg import ConstArg
    from guppylang_internals.tys.param import Parameter
    from guppylang_internals.tys.subst import PartialInst, Subst
    from guppylang_internals.tys.ty import Type


@dataclass(frozen=True)
class ConstBase(Transformable["Const"], ABC):
    """Abstract base class for constants arguments in the type system.

    In principle, we can allow constants of any type representable in the type system.
    For now, we will only support basic consts like `int` or `bool`, but in the future
    we could have struct constants etc.
    """

    ty: "Type" = field(compare=False, hash=False)  # Types are not hashable

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
        if not visitor.visit(self):
            visitor.visit(self.ty)

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
class ComptimeConstValue(ConstBase):
    """A constant value in the type system backed by a Python comptime expression.

    For example, in the type `array[int, comptime(n + 1)]` the second argument is a
    `ConstArg` that contains a `ComptimeConstValue`.
    """

    expr: "ComptimeExpr"

    #: Generic parameters that are in scope for this comptime value
    params: Sequence["Parameter"] = field(hash=False)

    #: Partial instantiation of those parameters
    inst: "PartialInst"

    #: Id of the definition in which this comptime value occurs. This will be used
    #: later to determine the globals that are in scope for this comptime expression.
    containing_def_id: DefId

    def cast(self) -> "Const":
        """Casts an implementor of `ConstBase` into a `Const`."""
        return self

    def transform(self, transformer: Transformer, /) -> "Const":
        """Accepts a transformer on this constant."""
        if const := transformer.transform(self):
            assert isinstance(const, ConstBase)
            return const.cast()
        return ComptimeConstValue(
            self.ty.transform(transformer),
            self.expr,
            self.params,
            tuple(arg.transform(transformer) if arg else None for arg in self.inst),
            self.containing_def_id,
        ).try_resolve(require_monomorphization=False)

    def try_resolve(self, require_monomorphization: bool) -> "Const":
        """Tries to evaluate the comptime expression using the current stashed partial
        instantiation.

        Returns the concrete constant value, or `self` of the expression cannot be
        evaluated yet.

        If `require_monomorphization=True`, then `RequiresMonomorphizationError` will
        be thrown when evaluating the expression would need concrete monomorphized
        values for the instantiation.
        """
        from guppylang_internals.checker.core import (
            Context,
            DummyEvalDict,
            Globals,
            Locals,
        )
        from guppylang_internals.checker.expr_checker import eval_comptime_expr
        from guppylang_internals.engine import DEF_STORE
        from guppylang_internals.tys.arg import ConstArg
        from guppylang_internals.tys.parsing import check_comptime_value

        inst = {
            param.name: arg or param.to_existential()[0]
            for param, arg in zip(self.params, self.inst, strict=True)
        }
        globals = Globals(DEF_STORE.frames[self.containing_def_id])
        ctx = Context(globals, Locals({}), inst)
        try:
            v = eval_comptime_expr(self.expr, ctx)
        except DummyEvalDict.UnsolvedExistentialError:
            return self
        except RequiresMonomorphizationError:
            if require_monomorphization:
                raise
            return self
        arg = check_comptime_value(v, self.expr)
        assert isinstance(arg, ConstArg)
        return arg.const


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

    def transform(self, transformer: Transformer, /) -> "ExistentialConstVar":
        """Accepts a transformer on this constant."""
        return transformer.transform(self) or ExistentialConstVar(
            self.ty.transform(transformer) or self.ty, self.display_name, self.id
        )


type Const = ConstValue | ComptimeConstValue | BoundConstVar | ExistentialConstVar
