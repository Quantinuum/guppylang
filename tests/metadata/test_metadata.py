"""Unit tests for metadata helpers."""

import pytest
from guppylang_internals.error import GuppyError
from guppylang_internals.metadata.common import (
    FunctionMetadata,
    MetadataAlreadySetError,
    ReservedMetadataKeysError,
    add_metadata,
)
from hugr.metadata import NodeMetadata


def test_add_metadata():
    node_metadata = NodeMetadata({"some-key": "some-value"})

    guppy_metadata = FunctionMetadata()
    guppy_metadata.set_expected_qubits(5)
    add_metadata(node_metadata, guppy_metadata)

    assert node_metadata.as_dict() == {
        "some-key": "some-value",
        "tket.hint.expected_qubits": 5,
    }


def test_add_additional_metadata():
    node_metadata = NodeMetadata({"some-key": "some-value"})

    add_metadata(node_metadata, additional_metadata={"more-key": "more-value"})

    assert node_metadata.as_dict() == {
        "some-key": "some-value",
        "more-key": "more-value",
    }


def test_add_metadata_no_reserved_metadata():
    node_metadata = NodeMetadata({})

    with pytest.raises(
        GuppyError,
        check=lambda e: (
            isinstance(e.error, ReservedMetadataKeysError)
            and e.error.keys == {"tket.hint.expected_qubits"}
        ),
    ):
        add_metadata(
            node_metadata, additional_metadata={"tket.hint.expected_qubits": 3}
        )


def test_add_metadata_metadata_already_set():
    node_metadata = NodeMetadata(
        {
            "tket.hint.expected_qubits": 1,
            "preset-key": "preset-value",
        }
    )

    guppy_metadata = FunctionMetadata()
    guppy_metadata.set_expected_qubits(5)
    with pytest.raises(
        GuppyError,
        check=lambda e: (
            isinstance(e.error, MetadataAlreadySetError)
            and e.error.key == "tket.hint.expected_qubits"
        ),
    ):
        add_metadata(node_metadata, guppy_metadata)

    with pytest.raises(
        GuppyError,
        check=lambda e: (
            isinstance(e.error, MetadataAlreadySetError) and e.error.key == "preset-key"
        ),
    ):
        add_metadata(node_metadata, additional_metadata={"preset-key": "preset-value"})


def test_add_metadata_property_inline():
    from tket.metadata import InlineAnnotation

    node_metadata = NodeMetadata({})

    guppy_metadata = FunctionMetadata()
    guppy_metadata.set_inline("best_effort")
    add_metadata(node_metadata, guppy_metadata)

    assert node_metadata.as_dict() == {InlineAnnotation.KEY: "best_effort"}
