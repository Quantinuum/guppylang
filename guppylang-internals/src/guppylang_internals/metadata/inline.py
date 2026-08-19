from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, cast

from hugr.metadata import Metadata
from hugr.utils import JsonType

InlineOptions = Literal["best_effort", "never"]

INLINE_OPTIONS: Sequence[InlineOptions] = ["best_effort", "never"]


@dataclass(frozen=True)
class MetadataInline(Metadata[InlineOptions]):
    KEY = "tket.inline"

    @classmethod
    def to_json(cls, value: InlineOptions) -> JsonType:
        return value

    @classmethod
    def from_json(cls, value: JsonType) -> InlineOptions:
        if value in INLINE_OPTIONS:
            return cast("InlineOptions", value)
        expected = " or ".join(f"'{opt}'" for opt in INLINE_OPTIONS)
        raise TypeError(
            f"Expected {expected} for MetadataInline, but got "
            + (f"'{value}'" if isinstance(value, str) else f"a {type(value)}")
        )
