from dataclasses import dataclass
from typing import ClassVar

from guppylang_internals.diagnostic import Error, Note


@dataclass(frozen=True)
class UnsupportedError(Error):
    title: ClassVar[str] = "Unsupported"
    span_label: ClassVar[str] = "{things} {is_are} not supported{extra}"
    things: str
    singular: bool = False
    unsupported_in: str = ""

    @property
    def is_are(self) -> str:
        return "is" if self.singular else "are"

    @property
    def extra(self) -> str:
        return f" in {self.unsupported_in}" if self.unsupported_in else ""


@dataclass(frozen=True)
class UnexpectedError(Error):
    title: ClassVar[str] = "Unexpected {things}"
    span_label: ClassVar[str] = "Unexpected {things}{extra}"
    things: str
    unexpected_in: str = ""

    @property
    def extra(self) -> str:
        return f" in {self.unexpected_in}" if self.unexpected_in else ""


@dataclass(frozen=True)
class ExpectedError(Error):
    title: ClassVar[str] = "Expected {things}"
    span_label: ClassVar[str] = "Expected {things}{extra}"
    things: str
    got: str = ""

    @property
    def extra(self) -> str:
        return f", got {self.got}" if self.got else ""


@dataclass(frozen=True)
class UnknownModifierError(Error):
    title: ClassVar[str] = "Unknown modifier"
    span_label: ClassVar[str] = (
        "Expected one of {{dagger, control(...), or power(...)}}"
    )


@dataclass(frozen=True)
class UnexpectedInWithBlockError(Error):
    title: ClassVar[str] = "Unexpected {kind}"
    span_label: ClassVar[str] = "{things} found in a `With` block"
    kind: str
    things: str

    @dataclass(frozen=True)
    class Modifier(Note):
        span_label: ClassVar[str] = "modifier is used here"


@dataclass(frozen=True)
class InvalidUnderDagger(Error):
    title: ClassVar[str] = "Invalid expression in dagger"
    span_label: ClassVar[str] = "{things} found in a dagger context"
    things: str

    @dataclass(frozen=True)
    class Dagger(Note):
        span_label: ClassVar[str] = "dagger modifier is used here"
