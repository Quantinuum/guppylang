"""Metadata attached to objects within the Guppy compiler, both for internal use and to
attach to HUGR nodes for lower-level processing."""

from abc import ABC
from dataclasses import dataclass, field, fields
from typing import Any, ClassVar, Generic, TypeVar

from hugr.hugr.node_port import ToNode

from guppylang_internals.diagnostic import Fatal
from guppylang_internals.error import GuppyError

T = TypeVar("T")


@dataclass(init=True, kw_only=True)
class GuppyMetadataValue(ABC, Generic[T]):
    """A template class for a metadata value within the scope of the Guppy compiler.
    Implementations should provide the `key` in reverse-URL format."""

    key: ClassVar[str]
    value: T | None = None


class MetadataMaxQubits(GuppyMetadataValue[int]):
    key = "tket.hint.max_qubits"


@dataclass(frozen=True, init=True, kw_only=True)
class GuppyMetadata:
    """DTO for metadata within the scope of the guppy compiler for attachment to HUGR
    nodes. See `add_metadata`."""

    max_qubits: MetadataMaxQubits = field(default_factory=MetadataMaxQubits, init=False)

    @classmethod
    def reserved_keys(cls) -> set[str]:
        return {f.type.key for f in fields(GuppyMetadata)}


@dataclass(frozen=True)
class MetadataAlreadySetError(Fatal):
    title: ClassVar[str] = "Metadata key already set"
    message: ClassVar[str] = "Received two values for the metadata key `{key}`"
    key: str


@dataclass(frozen=True)
class ReservedMetadataKeysError(Fatal):
    title: ClassVar[str] = "Metadata key is reserved"
    message: ClassVar[str] = (
        "The following metadata keys are reserved by Guppy but also provided in "
        "additional metadata: `{keys}`"
    )
    keys: set[str]


def add_metadata(
    node: ToNode,
    metadata: GuppyMetadata | None = None,
    *,
    additional_metadata: dict[str, Any] | None = None,
) -> None:
    """Adds metadata to the given node using the keys defined through inheritors of
    `GuppyMetadataValue` defined in the `GuppyMetadata` class.

    Additional metadata is forwarded as is, although the given dictionary may not
    contain any keys already reserved by fields in `GuppyMetadata`.
    """
    if metadata is not None:
        for f in fields(GuppyMetadata):
            data: GuppyMetadataValue[Any] = getattr(metadata, f.name)
            if data.key in node.metadata:
                raise GuppyError(MetadataAlreadySetError(None, data.key))
            if data.value is not None:
                node.metadata[data.key] = data.value

    if additional_metadata is not None:
        reserved_keys = GuppyMetadata.reserved_keys()
        used_reserved_keys = reserved_keys.intersection(additional_metadata.keys())
        if len(used_reserved_keys) > 0:
            raise GuppyError(ReservedMetadataKeysError(None, keys=used_reserved_keys))

        for key, value in additional_metadata.items():
            if key in node.metadata:
                raise GuppyError(MetadataAlreadySetError(None, key))
            node.metadata[key] = value
