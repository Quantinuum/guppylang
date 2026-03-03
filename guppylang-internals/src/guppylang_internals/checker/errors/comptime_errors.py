from dataclasses import dataclass
from typing import ClassVar

from guppylang_internals.checker.core import Place
from guppylang_internals.diagnostic import Error, Help, Note
from guppylang_internals.tys.ty import FunctionType


@dataclass(frozen=True)
class IllegalComptimeExpressionError(Error):
    title: ClassVar[str] = "Unsupported Python expression"
    span_label: ClassVar[str] = "Expression of type `{python_ty}` is not supported"
    python_ty: type

    @dataclass(frozen=True)
    class InContainer(Note):
        message: ClassVar[str] = (
            "Unsupported value was found inside a `{container_ty.__name__}`"
        )
        container_ty: type


@dataclass(frozen=True)
class ComptimeExprNotCPythonError(Error):
    title: ClassVar[str] = "Not running CPython"
    span_label: ClassVar[str] = "Comptime expressions are only supported in CPython"


@dataclass(frozen=True)
class ComptimeExprNotStaticError(Error):
    title: ClassVar[str] = "Not compile-time evaluatable"
    span_label: ClassVar[str] = (
        "Guppy variable `{guppy_var}` cannot be accessed in a comptime expression"
    )
    guppy_var: str


@dataclass(frozen=True)
class ComptimeExprEvalError(Error):
    title: ClassVar[str] = "Python error"
    span_label: ClassVar[str] = (
        "Error occurred while evaluating this comptime expression"
    )
    message: ClassVar[str] = "Traceback printed below:\n\n{err}"
    err: str


@dataclass(frozen=True)
class ComptimeExprIncoherentListError(Error):
    title: ClassVar[str] = "Unsupported list"
    span_label: ClassVar[str] = "List contains elements with different types"


@dataclass(frozen=True)
class PytketSignatureMismatch(Error):
    title: ClassVar[str] = "Signature mismatch"
    span_label: ClassVar[str] = "Signature `{name}` doesn't match provided circuit"
    name: str

    @dataclass(frozen=True)
    class TypeHint(Note):
        message: ClassVar[str] = "Expected circuit signature is `{circ_sig}`"
        circ_sig: FunctionType


@dataclass(frozen=True)
class ComptimeUnknownError(Error):
    title: ClassVar[str] = "Not known at compile-time"
    span_label: ClassVar[str] = "Value of this {thing} must be known at compile-time"
    thing: str

    @dataclass(frozen=True)
    class InputHint(Help):
        span_label: ClassVar[str] = (
            "`{place.root}` is a function argument, so its value is not statically "
            "known. Consider turning `{place.root}` into a comptime argument: "
            "`{place.root}: @comptime`"
        )
        place: Place

    @dataclass(frozen=True)
    class VariableHint(Note):
        span_label: ClassVar[str] = (
            "`{place.root}` is a dynamic variable, so its value is not statically known"
        )
        place: Place

    @dataclass(frozen=True)
    class FallbackHint(Note):
        span_label: ClassVar[str] = (
            "This expression involves a dynamic computation, so its value is not "
            "statically known"
        )

    @dataclass(frozen=True)
    class Feedback(Note):
        message: ClassVar[str] = (
            "We are currently investigating ways to make Guppy's compile-time "
            "reasoning smarter. Please leave your feedback at "
            "https://github.com/CQCL/guppylang/discussions/987"
        )
