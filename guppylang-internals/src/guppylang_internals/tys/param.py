from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, TypeAlias

from hugr import tys as ht
from typing_extensions import Self

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.errors.generic import ExpectedError
from guppylang_internals.checker.errors.type_errors import TypeMismatchError
from guppylang_internals.error import GuppyError, GuppyTypeError, InternalGuppyError
from guppylang_internals.tys.arg import Argument, ConstArg, TypeArg
from guppylang_internals.tys.common import ToHugr, ToHugrContext
from guppylang_internals.tys.const import BoundConstVar, ExistentialConstVar
from guppylang_internals.tys.errors import WrongNumberOfTypeArgsError
from guppylang_internals.tys.var import ExistentialVar

if TYPE_CHECKING:
    from guppylang_internals.tys.subst import PartialInst
    from guppylang_internals.tys.ty import Type

# We define the `Parameter` type as a union of all `ParameterBase` subclasses defined
# below. This models an algebraic data type and enables exhaustiveness checking in
# pattern matches etc.
# Note that this might become obsolete in case the `@sealed` decorator is added:
#  * https://peps.python.org/pep-0622/#sealed-classes-as-algebraic-data-types
#  * https://github.com/johnthagen/sealed-typing-pep
Parameter: TypeAlias = "TypeParam | ConstParam"


@dataclass(frozen=True)
class ParameterBase(ToHugr[ht.TypeParam], ABC):
    """Abstract base class for parameters used in function and type definitions.

    For example, when defining a struct type

    ```
    @guppy.struct
    class Foo[T, n: int]:
        ...
    ```

    we generate an `StructDef` that depends on the parameters `T` and `n`. From
    this, we obtain a proper `StructType` by providing arguments that are substituted
    for the parameters (for example `Foo[int, 42]`).
    """

    idx: int
    name: str

    @abstractmethod
    def with_idx(self, idx: int) -> Self:
        """Returns a copy of the parameter with a new index."""

    @abstractmethod
    def check_arg(self, arg: Argument, loc: AstNode | None = None) -> Argument:
        """Checks that this parameter can be instantiated with a given argument.

        Raises a user error if the argument is not valid.
        """

    @abstractmethod
    def to_existential(self) -> tuple[Argument, ExistentialVar]:
        """Creates a fresh existential variable that can be instantiated for this
        parameter.

        Returns both the argument and the created variable.
        """

    @abstractmethod
    def to_bound(self, idx: int | None = None) -> Argument:
        """Creates a bound variable with a given index that can be instantiated for this
        parameter.
        """

    @abstractmethod
    def instantiate_bounds(self, inst: "PartialInst") -> Self:
        """Instantiates bound variables mentioned in parameter bounds"""


@dataclass(frozen=True)
class TypeParam(ParameterBase):
    """A parameter of kind type. Used to define generic functions and types."""

    must_be_copyable: bool
    must_be_droppable: bool

    @property
    def can_be_linear(self) -> bool:
        """Whether this type should be treated linearly."""
        return not self.must_be_copyable and not self.must_be_droppable

    def with_idx(self, idx: int) -> "TypeParam":
        """Returns a copy of the parameter with a new index."""
        return TypeParam(idx, self.name, self.must_be_copyable, self.must_be_droppable)

    def check_arg(self, arg: Argument, loc: AstNode | None = None) -> TypeArg:
        """Checks that this parameter can be instantiated with a given argument.

        Raises a user error if the argument is not valid.
        """
        match arg:
            case ConstArg(const):
                err = ExpectedError(loc, "a type", got=f"value of type `{const.ty}`")
                raise GuppyTypeError(err)
            case TypeArg(ty):
                if self.must_be_copyable and not ty.copyable:
                    err = ExpectedError(
                        loc,
                        "a copyable type",
                        got=f"type `{ty}` which is not implicitly copyable",
                    )
                    raise GuppyTypeError(err)
                if self.must_be_droppable and not ty.droppable:
                    err = ExpectedError(
                        loc,
                        "a droppable type",
                        got=f"type `{ty}` which is not implicitly droppable",
                    )
                    raise GuppyTypeError(err)
                return arg

    def to_existential(self) -> tuple[Argument, ExistentialVar]:
        """Creates a fresh existential variable that can be instantiated for this
        parameter.

        Returns both the argument and the created variable.
        """
        from guppylang_internals.tys.ty import ExistentialTypeVar

        var = ExistentialTypeVar.fresh(
            self.name, self.must_be_copyable, self.must_be_droppable
        )
        return TypeArg(var), var

    def to_bound(self, idx: int | None = None) -> TypeArg:
        """Creates a bound variable with a given index that can be instantiated for this
        parameter.
        """
        from guppylang_internals.tys.ty import BoundTypeVar

        if idx is None:
            idx = self.idx
        return TypeArg(
            BoundTypeVar(self.name, idx, self.must_be_copyable, self.must_be_droppable)
        )

    def instantiate_bounds(self, inst: "PartialInst") -> "TypeParam":
        """Instantiates bound variables mentioned in parameter bounds"""
        # For now, type parameters don't have any bounds that could be instantiated
        return self

    def to_hugr(self, ctx: ToHugrContext) -> ht.TypeParam:
        """Computes the Hugr representation of the parameter."""
        return ht.TypeTypeParam(
            bound=ht.TypeBound.Copyable
            if self.must_be_copyable
            else ht.TypeBound.Linear
        )

    def __str__(self) -> str:
        """User-facing string representation of the parameter."""
        return self.name


@dataclass(frozen=True)
class ConstParam(ParameterBase):
    """A parameter of kind constant. Used to define fixed-size arrays etc."""

    ty: "Type" = field(hash=False)

    #: Marker to annotate if this parameter was implicitly generated by a `@comptime`
    #: annotated argument in a function signature.
    from_comptime_arg: bool = field(default=False, kw_only=True)

    def with_idx(self, idx: int) -> "ConstParam":
        """Returns a copy of the parameter with a new index."""
        return ConstParam(idx, self.name, self.ty)

    def check_arg(self, arg: Argument, loc: AstNode | None = None) -> ConstArg:
        """Checks that this parameter can be instantiated with a given argument.

        Raises a user error if the argument is not valid.
        """
        from guppylang_internals.tys.ty import unify

        match arg:
            case ConstArg(const):
                subst = unify(const.ty, self.ty, {})
                if subst is None:
                    raise GuppyTypeError(
                        TypeMismatchError(loc, self.ty, const.ty, kind="argument")
                    )
                return ConstArg(replace(const, ty=const.ty.substitute(subst)))
            case TypeArg(ty=ty):
                err = ExpectedError(
                    loc, f"expression of type `{self.ty}`", got=f"type `{ty}`"
                )
                raise GuppyTypeError(err)

    def to_existential(self) -> tuple[Argument, ExistentialVar]:
        """Creates a fresh existential variable that can be instantiated for this
        parameter.

        Returns both the argument and the created variable.
        """
        var = ExistentialConstVar.fresh(self.name, self.ty)
        return ConstArg(var), var

    def to_bound(self, idx: int | None = None) -> ConstArg:
        """Creates a bound variable with a given index that can be instantiated for this
        parameter.
        """
        if idx is None:
            idx = self.idx
        return ConstArg(BoundConstVar(self.ty, self.name, idx))

    def instantiate_bounds(self, inst: "PartialInst") -> "ConstParam":
        """Instantiates bound variables mentioned in parameter bounds"""
        from guppylang_internals.tys.subst import Instantiator

        instantiator = Instantiator(inst)
        return replace(self, ty=self.ty.transform(instantiator))

    def to_hugr(self, ctx: ToHugrContext) -> ht.TypeParam:
        """Computes the Hugr representation of the parameter."""
        from guppylang_internals.tys.ty import NumericType

        match self.ty:
            case NumericType(kind=NumericType.Kind.Nat):
                return ht.BoundedNatParam(upper_bound=None)
            case _:
                raise InternalGuppyError(
                    "Tried to convert non-nat const type parameter to Hugr. This "
                    "should have been monomorphized away."
                )

    def __str__(self) -> str:
        """User-facing string representation of the parameter."""
        return f"{self.name}: {self.ty}"


def check_all_args(
    params: Sequence[Parameter],
    args: Sequence[Argument],
    type_name: str,
    loc: AstNode | None = None,
    arg_locs: Sequence[AstNode] | None = None,
) -> None:
    """Checks a list of arguments against the given parameters.

    Raises a user error if number of arguments doesn't match or one of the argument is
    invalid.
    """
    exp, act = len(params), len(args)
    if exp != act:
        # TODO: Adjust the error span to only point to the offending arguments (similar
        #  to how we deal with call args in the expression checker). This requires
        #  threading the type arg spans down to this point
        raise GuppyError(WrongNumberOfTypeArgsError(loc, exp, act, type_name))

    # Now check that the kinds match up
    for i, (param, arg) in enumerate(zip(params, args, strict=True)):
        arg_loc = arg_locs[i] if arg_locs else loc
        param.instantiate_bounds(args).check_arg(arg, arg_loc)
