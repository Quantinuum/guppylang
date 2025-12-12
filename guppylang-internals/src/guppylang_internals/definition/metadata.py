from dataclasses import dataclass, field, fields
from typing import Any, ClassVar, Generic, TypeVar

from hugr.hugr.node_port import ToNode

from guppylang_internals.diagnostic import Fatal
from guppylang_internals.error import GuppyError

T = TypeVar("T")


@dataclass(init=True, kw_only=True)
class GuppyMetadataValue(Generic[T]):
    key: ClassVar[str]
    value: T | None = None


class MetadataMaxQubits(GuppyMetadataValue[int]):
    key = "tket.hint.max_qubits"


@dataclass(frozen=True, init=True, kw_only=True)
class GuppyMetadata:
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
        "The following metadata keys are reserved by Guppy but provided in additional "
        "metadata: `{keys}`"
    )
    keys: set[str]


def add_metadata(
    node: ToNode,
    metadata: GuppyMetadata | None = None,
    *,
    additional_metadata: dict[str, Any] | None = None,
) -> None:
    """Adds metadata to the given node, using standard keys for defined fields of the
    `Metadata` instance and forwarding surplus keyword arguments as is.
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
