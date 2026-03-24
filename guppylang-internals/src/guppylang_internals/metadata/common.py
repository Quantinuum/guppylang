from dataclasses import dataclass, field
from typing import Any, ClassVar

from hugr.debug_info import DebugRecord
from hugr.hugr.node_port import ToNode
from hugr.metadata import HugrDebugInfo, NodeMetadata
from hugr.utils import JsonType

from guppylang_internals.diagnostic import Fatal
from guppylang_internals.error import GuppyError
from guppylang_internals.metadata.max_qubits import MetadataMaxQubits


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


@dataclass
class FunctionMetadata:
    """Class for storing metadata to be attached to Hugr nodes during compilation."""

    _node_metadata: NodeMetadata = field(default_factory=NodeMetadata)
    _RESERVED_KEYS: ClassVar[set[str]] = {
        HugrDebugInfo.KEY,
        MetadataMaxQubits.KEY,
    }

    def as_dict(self) -> dict[str, JsonType]:
        return self._node_metadata.as_dict()

    def set_debug_info(self, debug_info: DebugRecord) -> None:
        self._node_metadata[HugrDebugInfo] = debug_info

    def set_max_qubits(self, max_qubits: int) -> None:
        self._node_metadata[MetadataMaxQubits] = max_qubits

    def get_debug_info(self) -> DebugRecord | None:
        debug_record = self._node_metadata.get(HugrDebugInfo, None)
        assert debug_record is None or isinstance(debug_record, DebugRecord)
        return debug_record

    def get_max_qubits(self) -> int | None:
        qubits = self._node_metadata.get(MetadataMaxQubits, None)
        assert qubits is None or isinstance(qubits, int)
        return qubits

    @classmethod
    def reserved_keys(cls) -> set[str]:
        return cls._RESERVED_KEYS


def add_metadata(
    node: ToNode,
    metadata: FunctionMetadata | None = None,
    *,
    additional_metadata: dict[str, Any] | None = None,
) -> None:
    """Extends metadata of a node, ensuring reserved keys aren't overwritten."""
    if metadata is not None:
        metadata_dict = metadata.as_dict()
        for key in metadata_dict:
            if key in node.metadata:
                raise GuppyError(MetadataAlreadySetError(None, key))
            if metadata_dict[key] is not None:
                node.metadata[key] = metadata_dict[key]

    if additional_metadata is not None:
        reserved_keys = FunctionMetadata.reserved_keys()
        used_reserved_keys = reserved_keys.intersection(additional_metadata.keys())
        if len(used_reserved_keys) > 0:
            raise GuppyError(ReservedMetadataKeysError(None, keys=used_reserved_keys))

        for key, value in additional_metadata.items():
            if key in node.metadata:
                raise GuppyError(MetadataAlreadySetError(None, key))
            node.metadata[key] = value
