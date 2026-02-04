from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from guppylang_internals.diagnostic import Error, Help, Note

if TYPE_CHECKING:
    from guppylang_internals.definition.struct import StructField
    from guppylang_internals.tys.const import Const
    from guppylang_internals.tys.param import TypeParam
    from guppylang_internals.tys.ty import FunctionType, Type


@dataclass(frozen=True)
class TypeMismatchError(Error):
    title: ClassVar[str] = "Type mismatch"
    span_label: ClassVar[str] = "Expected {kind} of type `{expected}`, got `{actual}`"

    expected: Type
    actual: Type
    kind: str = "expression"

    @dataclass(frozen=True)
    class CantInferParam(Note):
        message: ClassVar[str] = (
            "Couldn't infer an instantiation for type variable `?{type_var}` "
            "(higher-rank polymorphic types are not supported)"
        )
        type_var: str

    @dataclass(frozen=True)
    class CantInstantiateFreeVars(Note):
        message: ClassVar[str] = (
            "Can't instantiate parameter `{param}` with type `{illegal_inst}` "
            "containing free variables"
        )
        param: str
        illegal_inst: Type | Const


@dataclass(frozen=True)
class ConstMismatchError(Error):
    title: ClassVar[str] = "Value mismatch"
    span_label: ClassVar[str] = "Expected constant `{expected}`, got `{actual}`"

    expected: Const
    actual: Const


@dataclass(frozen=True)
class AssignFieldTypeMismatchError(Error):
    title: ClassVar[str] = "Type mismatch"
    span_label: ClassVar[str] = (
        "Cannot assign expression of type `{actual}` to field `{field.name}` of type "
        "`{field.ty}`"
    )
    actual: Type
    field: StructField


@dataclass(frozen=True)
class AssignSubscriptTypeMismatchError(Error):
    title: ClassVar[str] = "Type mismatch"
    span_label: ClassVar[str] = (
        "Cannot assign expression of type `{actual}` to array element of type "
        "`{expected}`"
    )
    actual: Type
    expected: Type


@dataclass(frozen=True)
class NonLinearInstantiateError(Error):
    title: ClassVar[str] = "Not defined for linear argument"
    span_label: ClassVar[str] = (
        "Cannot instantiate {expected} type parameter `{param.name}` in type "
        "`{func_ty}` with non-{expected} type `{ty}`"
    )
    param: TypeParam
    func_ty: FunctionType
    ty: Type

    @property
    def expected(self) -> str:
        return "copyable" if self.param.must_be_copyable else "droppable"


@dataclass(frozen=True)
class TypeInferenceError(Error):
    title: ClassVar[str] = "Cannot infer type"
    span_label: ClassVar[str] = (
        "Cannot infer type variables in expression of type `{unsolved_ty}`"
    )
    unsolved_ty: Type


@dataclass(frozen=True)
class ParameterInferenceError(Error):
    title: ClassVar[str] = "Cannot infer generic parameter"
    span_label: ClassVar[str] = (
        "Cannot infer generic parameter `{param}` of this function"
    )
    param: str

    @dataclass(frozen=True)
    class SignatureHint(Note):
        message: ClassVar[str] = "Function signature is `{sig}`"
        sig: FunctionType


@dataclass(frozen=True)
class IllegalConstant(Error):
    title: ClassVar[str] = "Unsupported constant"
    span_label: ClassVar[str] = "Type `{python_ty.__name__}` is not supported"
    python_ty: type


@dataclass(frozen=True)
class ModuleMemberNotFoundError(Error):
    title: ClassVar[str] = "Not found in module"
    span_label: ClassVar[str] = "Module `{module_name}` has no member `{member}`"
    module_name: str
    member: str


@dataclass(frozen=True)
class AttributeNotFoundError(Error):
    title: ClassVar[str] = "Attribute not found"
    span_label: ClassVar[str] = "`{ty}` has no attribute `{attribute}`"
    ty: Type
    attribute: str


@dataclass(frozen=True)
class UnaryOperatorNotDefinedError(Error):
    title: ClassVar[str] = "Operator not defined"
    span_label: ClassVar[str] = "Unary operator `{op}` not defined for `{ty}`"
    ty: Type
    op: str


@dataclass(frozen=True)
class BinaryOperatorNotDefinedError(Error):
    title: ClassVar[str] = "Operator not defined"
    span_label: ClassVar[str] = (
        "Binary operator `{op}` not defined for `{left_ty}` and `{right_ty}`"
    )
    left_ty: Type
    right_ty: Type
    op: str


@dataclass(frozen=True)
class BadProtocolError(Error):
    title: ClassVar[str] = "Not {is_not}"
    span_label: ClassVar[str] = "Expression of type `{ty}` is not {is_not}"
    ty: Type
    is_not: str

    @dataclass(frozen=True)
    class MethodMissing(Help):
        message: ClassVar[str] = "Implement missing method: `{method}: {signature}`"
        method: str
        signature: FunctionType

    @dataclass(frozen=True)
    class BadSignature(Help):
        message: ClassVar[str] = (
            "Fix signature of method `{ty}.{method}`:  Expected `{exp_signature}`, got "
            "`{act_signature}`"
        )
        ty: Type
        method: str
        exp_signature: FunctionType
        act_signature: FunctionType


@dataclass(frozen=True)
class MissingReturnValueError(Error):
    title: ClassVar[str] = "Missing return value"
    span_label: ClassVar[str] = "Expected return value of type `{ty}`"
    ty: Type


@dataclass(frozen=True)
class TypeApplyNotGenericError(Error):
    title: ClassVar[str] = "Not generic"
    span_label: ClassVar[str] = (
        "{thing} is not generic, so no type parameters can be provided"
    )
    func_name: str | None

    @property
    def thing(self) -> str:
        return f"`{self.func_name}`" if self.func_name else "This function"


@dataclass(frozen=True)
class NotCallableError(Error):
    title: ClassVar[str] = "Not callable"
    span_label: ClassVar[str] = "Expected a function, got expression of type `{actual}`"
    actual: Type


@dataclass(frozen=True)
class WrongNumberOfArgsError(Error):
    title: ClassVar[str] = ""  # Custom implementation in `rendered_title`
    expected: int
    actual: int
    detailed: bool = True
    is_type_apply: bool = False

    @property
    def rendered_title(self) -> str:
        return (
            f"Not enough {self.argument_kind}s"
            if self.expected > self.actual
            else f"Too many {self.argument_kind}s"
        )

    @property
    def argument_kind(self) -> str:
        return "type argument" if self.is_type_apply else "argument"

    @property
    def rendered_span_label(self) -> str:
        if not self.detailed:
            return f"Expected {self.expected}, got {self.actual}"
        diff = self.expected - self.actual
        if diff < 0:
            msg = f"Unexpected {self.argument_kind}"
            if diff < -1:
                msg += "s"
        else:
            msg = f"Missing {self.argument_kind}"
            if diff > 1:
                msg += "s"
        return f"{msg} (expected {self.expected}, got {self.actual})"

    @dataclass(frozen=True)
    class SignatureHint(Note):
        message: ClassVar[str] = "Function signature is `{sig}`"
        sig: FunctionType


@dataclass(frozen=True)
class WrongNumberOfUnpacksError(Error):
    title: ClassVar[str] = "{prefix} values to unpack"
    expected: int
    actual: int
    at_least: bool

    @property
    def prefix(self) -> str:
        return "Not enough" if self.expected > self.actual else "Too many"

    @property
    def rendered_span_label(self) -> str:
        diff = self.expected - self.actual
        if diff < 0:
            msg = "Unexpected assignment " + ("targets" if diff < -1 else "target")
            at_least = "at least " if self.at_least else ""
        else:
            msg = "Not enough assignment targets"
            assert not self.at_least
            at_least = ""
        return f"{msg} (expected {self.expected}, got {at_least}{self.actual})"


@dataclass(frozen=True)
class UnpackableError(Error):
    title: ClassVar[str] = "Unpackable"
    span_label: ClassVar[str] = "Expression of type `{ty}` cannot be unpacked"
    ty: Type

    @dataclass(frozen=True)
    class NonStaticIter(Note):
        message: ClassVar[str] = (
            "Unpacking of iterable types like `{ty}` is only allowed if the number of "
            "items yielded by the iterator is statically known. This is not the case "
            "for `{ty}`."
        )

    @dataclass(frozen=True)
    class GenericSize(Note):
        message: ClassVar[str] = (
            "Unpacking of iterable types like `{ty}` is only allowed if the number of "
            "items yielded by the iterator is statically known. Here, the number of "
            "items `{num}` is generic and can change between different function "
            "invocations."
        )
        num: Const


@dataclass(frozen=True)
class StarredTupleUnpackError(Error):
    title: ClassVar[str] = "Invalid starred unpacking"
    span_label: ClassVar[str] = (
        "Expression of type `{ty}` cannot be collected into a starred assignment since "
        "the yielded items have different types"
    )
    ty: Type


@dataclass(frozen=True)
class AssignNonPlaceHelp(Help):
    message: ClassVar[str] = (
        "Consider assigning this value to a local variable first before assigning the "
        "field `{field.name}`"
    )
    field: StructField


@dataclass(frozen=True)
class ArrayComprUnknownSizeError(Error):
    title: ClassVar[str] = "Array comprehension with nonstatic size"
    span_label: ClassVar[str] = "Cannot infer the size of this array comprehension ..."

    @dataclass(frozen=True)
    class IfGuard(Note):
        span_label: ClassVar[str] = "since it depends on this condition"

    @dataclass(frozen=True)
    class DynamicIterator(Note):
        span_label: ClassVar[str] = (
            "since the number of elements yielded by this iterator is not statically "
            "known"
        )


@dataclass(frozen=True)
class TupleIndexOutOfBoundsError(Error):
    title: ClassVar[str] = "Tuple index out of bounds"
    span_label: ClassVar[str] = (
        "Tuple index `{index}` is out of bounds for tuple of size `{size}`"
    )
    index: int
    size: int


@dataclass(frozen=True)
class IntOverflowError(Error):
    title: ClassVar[str] = "Integer {over_under}flow"
    span_label: ClassVar[str] = (
        "Value does not fit into a {bits}-bit {signed_unsigned} integer"
    )
    signed: bool
    bits: int
    is_underflow: bool

    @property
    def over_under(self) -> str:
        return "under" if self.is_underflow else "over"

    @property
    def signed_unsigned(self) -> str:
        return "signed" if self.signed else "unsigned"
