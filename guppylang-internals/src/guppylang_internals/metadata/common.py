from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, cast, get_args

from hugr.debug_info import DebugRecord
from hugr.metadata import HugrDebugInfo, Metadata, NodeMetadata
from hugr.utils import JsonType

from guppylang_internals.debug_mode import debug_mode_enabled
from guppylang_internals.diagnostic import Fatal
from guppylang_internals.error import GuppyError
from guppylang_internals.metadata.expected_qubits import MetadataExpectedQubitsHint

if TYPE_CHECKING:
    from tket.metadata import InlineAnnotationValue


class MetadataUnitaryFlags(Metadata[int]):
    """stub implementation of `tket.metadata.UnitaryFlags` to ensure decoupling between
    guppy and tket. See:
    - `tests/test_guppy_decoupled.py:83`
    - https://github.com/Quantinuum/guppylang/issues/1595"""

    KEY = "tket.unitary"


class DaggeredImplementation(Metadata[str]):
    """stub implementation for tket.metadata.DaggeredImplementation to ensure decoupling
    between guppy and tket. See:
    - `tests/test_guppy_decoupled.py:83`
    - https://github.com/Quantinuum/guppylang/issues/1595"""

    KEY = "tket.daggered"


class ControlledImplementations(Metadata[list[str]]):
    """stub implementation for tket.metadata.ControlledImplementations to ensure
    decoupling between guppy and tket. See:
    - `tests/test_guppy_decoupled.py:83`
    - https://github.com/Quantinuum/guppylang/issues/1595"""

    KEY = "tket.controlled"


class CtrlDaggeredImplementations(Metadata[list[str]]):
    """stub implementation for tket.metadata.CtrlDaggeredImplementations to ensure
    decoupling between guppy and tket. See:
    - `tests/test_guppy_decoupled.py:83`
    - https://github.com/Quantinuum/guppylang/issues/1595"""

    KEY = "tket.ctrl_daggered"


class NumControlQubits(Metadata[int]):
    """stub implementation for tket.metadata.NumControlQubits to ensure decoupling
    between guppy and tket. See:
    - `tests/test_guppy_decoupled.py:83`
    - https://github.com/Quantinuum/guppylang/issues/1595"""

    KEY = "tket.num_control_qubits"


# Metadata keys for modified definitions (daggered, controlled, ctrl-daggered)
# To be removed when added to tket
DAGGERED_KEY = DaggeredImplementation.KEY
CONTROLLED_KEY = ControlledImplementations.KEY
CTRL_DAGGERED_KEY = CtrlDaggeredImplementations.KEY
NUM_CONTROL_QUBITS_KEY = NumControlQubits.KEY


@dataclass(frozen=True)
class MetadataAlreadySetError(Fatal):
    title: ClassVar[str] = "Metadata key already set"
    message: ClassVar[str] = "Received two values for the metadata key `{key}`"
    key: str


@dataclass(frozen=True)
class ReservedMetadataKeysError(Fatal):
    title: ClassVar[str] = "Metadata key is reserved"
    message: ClassVar[str] = "{rendered_message}"
    keys: set[str]

    @property
    def rendered_message(self) -> str:
        assert len(self.keys) > 0
        if len(self.keys) == 1:
            return (
                f"The metadata key `{next(iter(self.keys))}` cannot be used because "
                f"it is reserved by Guppy."
            )
        else:
            return (
                f"The metadata keys `{self.keys}` cannot be used because they are "
                f"reserved by Guppy."
            )


@dataclass
class FunctionMetadata:
    """Class for storing metadata to be attached to Hugr nodes during compilation."""

    _node_metadata: NodeMetadata = field(default_factory=NodeMetadata)
    _RESERVED_KEYS: ClassVar[set[str]] = {
        HugrDebugInfo.KEY,
        MetadataExpectedQubitsHint.KEY,
        MetadataUnitaryFlags.KEY,
        "tket.inline",  # InlineAnnotation.KEY # Not possible for decoupled tests
        DAGGERED_KEY,
        CONTROLLED_KEY,
        CTRL_DAGGERED_KEY,
        NUM_CONTROL_QUBITS_KEY,
    }

    def as_dict(self) -> dict[str, JsonType]:
        return self._node_metadata.as_dict()

    def set_debug_info(self, debug_info: DebugRecord) -> None:
        self._node_metadata[HugrDebugInfo] = debug_info

    def set_expected_qubits(self, expected_qubits: int) -> None:
        self._node_metadata[MetadataExpectedQubitsHint] = expected_qubits

    def set_inline(self, inline: "InlineAnnotationValue") -> None:
        from tket.metadata import InlineAnnotation, InlineAnnotationValue

        inline_options = get_args(InlineAnnotationValue)
        if inline not in inline_options:  # for anyone not using a typechecker
            expected = " or ".join(f"'{opt}'" for opt in inline_options)
            raise ValueError(
                f"Expected {expected} for InlineAnnotation, but got {inline!r}"
            )
        self._node_metadata[InlineAnnotation] = inline

    def set_unitary_flags(self, value: int) -> None:
        self._node_metadata[MetadataUnitaryFlags] = value

    def set_generic_metadata(self, key: str, value: JsonType) -> None:
        if key in FunctionMetadata.reserved_keys():
            raise GuppyError(ReservedMetadataKeysError(None, keys={key}))
        self._node_metadata[key] = value

    def get_debug_info(self) -> DebugRecord | None:
        debug_record = self._node_metadata.get(HugrDebugInfo, None)
        assert debug_record is None or isinstance(debug_record, DebugRecord)
        return debug_record

    def get_expected_qubits(self) -> int | None:
        qubits = self._node_metadata.get(MetadataExpectedQubitsHint, None)
        assert qubits is None or isinstance(qubits, int)
        return qubits

    def get_unitary_flags(self) -> int | None:
        flags = self._node_metadata.get(MetadataUnitaryFlags, None)
        assert flags is None or isinstance(flags, int)
        return flags

    def get_inline(self) -> "InlineAnnotationValue | None":
        from tket.metadata import InlineAnnotation

        return self._node_metadata.get(InlineAnnotation, None)

    @classmethod
    def reserved_keys(cls) -> set[str]:
        return cls._RESERVED_KEYS


def add_metadata(
    node_metadata: NodeMetadata,
    metadata: FunctionMetadata | None = None,
    *,
    additional_metadata: dict[str, Any] | None = None,
) -> None:
    """Extends metadata of a node, ensuring reserved keys aren't overwritten."""
    if metadata is not None:
        metadata_dict = metadata.as_dict()
        for key in metadata_dict:
            if key == HugrDebugInfo.KEY and not debug_mode_enabled():
                continue
            if key in node_metadata:
                raise GuppyError(MetadataAlreadySetError(None, key))
            if metadata_dict[key] is not None:
                node_metadata[key] = metadata_dict[key]

    if additional_metadata is not None:
        reserved_keys = FunctionMetadata.reserved_keys()
        used_reserved_keys = reserved_keys.intersection(additional_metadata.keys())
        if len(used_reserved_keys) > 0:
            raise GuppyError(ReservedMetadataKeysError(None, keys=used_reserved_keys))

        for key, value in additional_metadata.items():
            if key in node_metadata:
                raise GuppyError(MetadataAlreadySetError(None, key))
            node_metadata[key] = value


def add_unitary_metadata(
    node_metadata: NodeMetadata,
    unitary_flag: int,
) -> None:
    """Adds unitary flag to the metadata of a node, ensuring reserved keys aren't
    overwritten."""
    if MetadataUnitaryFlags.KEY in node_metadata:
        raise GuppyError(MetadataAlreadySetError(None, MetadataUnitaryFlags.KEY))
    node_metadata[MetadataUnitaryFlags.KEY] = unitary_flag


def add_custom_implementations(
    node_metadata: NodeMetadata,
    *,
    daggered: str | None = None,
    controlled: list[str] | None = None,
    ctrl_daggered: list[str] | None = None,
) -> None:
    """Adds the names of the functions implementing custom modifications, ensuring
    reserved keys aren't overwritten."""
    if daggered is not None:
        if DAGGERED_KEY in node_metadata:
            raise GuppyError(MetadataAlreadySetError(None, DAGGERED_KEY))
        node_metadata[DAGGERED_KEY] = cast("JsonType", daggered)
    if controlled is not None:
        if CONTROLLED_KEY in node_metadata:
            raise GuppyError(MetadataAlreadySetError(None, CONTROLLED_KEY))
        node_metadata[CONTROLLED_KEY] = cast("JsonType", controlled)
    if ctrl_daggered is not None:
        if CTRL_DAGGERED_KEY in node_metadata:
            raise GuppyError(MetadataAlreadySetError(None, CTRL_DAGGERED_KEY))
        node_metadata[CTRL_DAGGERED_KEY] = cast("JsonType", ctrl_daggered)


def add_num_control_qubits(
    node_metadata: NodeMetadata,
    num_control_qubits: int,
) -> None:
    """Adds the number of control qubits, ensuring it isn't overwritten."""
    if NUM_CONTROL_QUBITS_KEY in node_metadata:
        raise GuppyError(MetadataAlreadySetError(None, NUM_CONTROL_QUBITS_KEY))
    node_metadata[NUM_CONTROL_QUBITS_KEY] = num_control_qubits
