from dataclasses import dataclass
from typing import ClassVar

from hugr.metadata import Metadata
from hugr.utils import JsonType


@dataclass(frozen=True)
class MetadataExpectedQubits(Metadata[int]):
    KEY = "tket.hint.expected_qubits"
    ALIASES: ClassVar[list[str]] = ["tket.hint.max_qubits"]

    @classmethod
    def to_json(cls, value: int) -> JsonType:
        return value

    @classmethod
    def from_json(cls, value: JsonType) -> int:
        if not isinstance(value, int):
            msg = (
                f"Expected an integer for MetadataExpectedQubits, but got {type(value)}"
            )
            raise TypeError(msg)
        return value
