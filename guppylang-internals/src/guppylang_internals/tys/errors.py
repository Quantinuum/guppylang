from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from guppylang_internals.diagnostic import Error, Help, Note

if TYPE_CHECKING:
    from guppylang_internals.definition.parameter import ParamDef
    from guppylang_internals.tys.ty import Type, UnitaryFlags


@dataclass(frozen=True)
class WrongNumberOfTypeArgsError(Error):
    title: ClassVar[str] = ""  # Custom implementation in `rendered_title`
    expected: int
    actual: int
    type_name: str

    @property
    def rendered_title(self) -> str:
        if self.expected == 0:
            return "Non-parametric type"
        elif self.expected > self.actual:
            return "Missing type arguments"
        else:
            return "Too many type arguments"

    @property
    def rendered_span_label(self) -> str:
        if self.expected == 0:
            return f"Type `{self.type_name}` is not parametric"
        diff = self.expected - self.actual
        msg = "Unexpected " if diff < 0 else "Missing "
        msg += "type arguments " if abs(diff) > 1 else "type argument "
        msg += (
            f"for type `{self.type_name}` (expected {self.expected}, got {self.actual})"
        )
        return msg


@dataclass(frozen=True)
class InvalidTypeArgError(Error):
    title: ClassVar[str] = "Invalid type argument"
    span_label: ClassVar[str] = "Not a valid type argument"


@dataclass(frozen=True)
class IllegalComptimeTypeArgError(Error):
    title: ClassVar[str] = "Invalid type argument"
    span_label: ClassVar[str] = (
        "Comptime expression evaluating to `{obj}` is not a valid type argument"
    )
    obj: object


@dataclass(frozen=True)
class ModuleMemberNotFoundError(Error):
    # TODO: Unify with the definition in expression checker once merged
    title: ClassVar[str] = "Not found in module"
    span_label: ClassVar[str] = "Module `{module_name}` has no member `{member}`"
    module_name: str
    member: str


@dataclass(frozen=True)
class HigherKindedTypeVarError(Error):
    title: ClassVar[str] = "Not parametric"
    span_label: ClassVar[str] = (
        "Type variable `{var_def.name}` doesn't take type arguments"
    )
    var_def: "ParamDef"

    @dataclass(frozen=True)
    class Explain(Note):
        message: ClassVar[str] = "Higher-kinded types are not supported"

    def __post_init__(self) -> None:
        self.add_sub_diagnostic(HigherKindedTypeVarError.Explain(None))


@dataclass(frozen=True)
class FreeTypeVarError(Error):
    title: ClassVar[str] = "Free type variable"
    span_label: ClassVar[str] = "Type variable `{var_def.name}` is unbound"
    var_def: "ParamDef"

    @dataclass(frozen=True)
    class Explain(Note):
        message: ClassVar[str] = (
            "Only struct and function definitions can be generic. Other generic values "
            "or nested types are not supported."
        )

    def __post_init__(self) -> None:
        self.add_sub_diagnostic(FreeTypeVarError.Explain(None))


@dataclass(frozen=True)
class InvalidTypeError(Error):
    title: ClassVar[str] = "Invalid type"
    span_label: ClassVar[str] = "Not a valid type"


@dataclass(frozen=True)
class InvalidCallableTypeError(Error):
    title: ClassVar[str] = "Invalid type"
    span_label: ClassVar[str] = "Invalid function type"

    @dataclass(frozen=True)
    class Explain(Help):
        message: ClassVar[str] = (
            "Function types are specified as follows: "
            "`Callable[[<arguments>], <return type>]`"
        )

    def __post_init__(self) -> None:
        self.add_sub_diagnostic(InvalidCallableTypeError.Explain(None))


@dataclass(frozen=True)
class SelfTyNotInMethodError(Error):
    title: ClassVar[str] = "Invalid type"
    span_label: ClassVar[str] = "`Self` type annotations are only allowed in methods"


@dataclass(frozen=True)
class NonLinearOwnedError(Error):
    title: ClassVar[str] = "Invalid annotation"
    span_label: ClassVar[str] = "Classical type `{ty}` cannot be owned"
    ty: "Type"


@dataclass(frozen=True)
class LinearConstParamError(Error):
    title: ClassVar[str] = "Invalid parameter"
    span_label: ClassVar[str] = (
        "Non-{thing} type `{ty}` is not allowed as a generic parameter"
    )
    ty: "Type"

    @property
    def thing(self) -> str:
        return "copyable" if not self.ty.copyable else "droppable"


@dataclass(frozen=True)
class LinearComptimeError(Error):
    title: ClassVar[str] = "Invalid annotation"
    span_label: ClassVar[str] = (
        "Non-{thing} type `{ty}` is not allowed as a comptime argument"
    )
    ty: "Type"

    @property
    def thing(self) -> str:
        return "copyable" if not self.ty.copyable else "droppable"


@dataclass(frozen=True)
class CallableComptimeError(Error):
    title: ClassVar[str] = "Invalid annotation"
    span_label: ClassVar[str] = (
        "Comptime annotations are only allowed for named top-level function arguments"
    )


@dataclass(frozen=True)
class ComptimeArgShadowError(Error):
    title: ClassVar[str] = "Shadowed type parameter"
    span_label: ClassVar[str] = (
        "Comptime argument `{arg}` shadows previously used parameter with the same name"
    )
    arg: str


@dataclass(frozen=True)
class InvalidFlagError(Error):
    title: ClassVar[str] = "Invalid annotation"
    span_label: ClassVar[str] = "Invalid type annotation"


@dataclass(frozen=True)
class FlagNotAllowedError(Error):
    title: ClassVar[str] = "Invalid annotation"
    span_label: ClassVar[str] = "`@` type annotations are not allowed in this position"


@dataclass(frozen=True)
class UnitaryCallError(Error):
    title: ClassVar[str] = "Unitary constraint violation"
    span_label: ClassVar[str] = (
        "This function cannot be called in a {render_flags} context"
    )
    flags: "UnitaryFlags"

    @property
    def render_flags(self) -> str:
        from guppylang_internals.tys.ty import UnitaryFlags

        if self.flags == UnitaryFlags.Dagger:
            return "dagger"
        elif self.flags == UnitaryFlags.Control:
            return "control"
        elif self.flags == UnitaryFlags.Power:
            return "power"
        else:
            return "unitary"
