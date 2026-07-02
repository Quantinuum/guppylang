from dataclasses import dataclass
from typing import Literal

from hugr.metadata import Metadata
from hugr.utils import JsonType


@dataclass(frozen=True)
class MetadataInline(Metadata[Literal["best_effort", "never"]]):
    KEY = "tket.inline"

    @classmethod
    def to_json(cls, value: Literal["best_effort", "never"]) -> JsonType:
        return value

    @classmethod
    def from_json(cls, value: JsonType) -> Literal["best_effort", "never"]:
        match value:
            case "best_effort" | "never":
                return value
            case _:
                raise TypeError(
                    "Expected 'best_effort' or 'never' for MetadataInline, but got "
                    + (f"'{value}'" if isinstance(value, str) else f"a {type(value)}")
                )
