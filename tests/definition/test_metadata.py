"""Unit tests for guppylang.emulator.builder module."""

from unittest.mock import Mock

import pytest
from guppylang_internals.definition.metadata import (
    GuppyMetadata,
    MetadataAlreadySetError,
    ReservedMetadataKeysError,
    add_metadata,
)
from guppylang_internals.error import GuppyError


def test_add_metadata():
    mock_hugr_node = Mock()
    mock_hugr_node.metadata = {"some-key": "some-value"}

    guppy_metadata = GuppyMetadata()
    guppy_metadata.max_qubits.value = 5
    add_metadata(mock_hugr_node, guppy_metadata)

    assert mock_hugr_node.metadata == {
        "some-key": "some-value",
        "tket.hint.max_qubits": 5,
    }


def test_add_additional_metadata():
    mock_hugr_node = Mock()
    mock_hugr_node.metadata = {"some-key": "some-value"}

    add_metadata(mock_hugr_node, additional_metadata={"more-key": "more-value"})

    assert mock_hugr_node.metadata == {
        "some-key": "some-value",
        "more-key": "more-value",
    }


def test_add_metadata_no_reserved_metadata():
    mock_hugr_node = Mock()
    mock_hugr_node.metadata = {}

    with pytest.raises(
        GuppyError,
        check=lambda e: (
            isinstance(e.error, ReservedMetadataKeysError)
            and e.error.keys == {"tket.hint.max_qubits"}
        ),
    ):
        add_metadata(mock_hugr_node, additional_metadata={"tket.hint.max_qubits": 3})


def test_add_metadata_metadata_already_set():
    mock_hugr_node = Mock()
    mock_hugr_node.metadata = {
        "tket.hint.max_qubits": 1,
        "preset-key": "preset-value",
    }

    guppy_metadata = GuppyMetadata()
    guppy_metadata.max_qubits.value = 5
    with pytest.raises(
        GuppyError,
        check=lambda e: (
            isinstance(e.error, MetadataAlreadySetError)
            and e.error.key == "tket.hint.max_qubits"
        ),
    ):
        add_metadata(mock_hugr_node, guppy_metadata)

    with pytest.raises(
        GuppyError,
        check=lambda e: (
            isinstance(e.error, MetadataAlreadySetError) and e.error.key == "preset-key"
        ),
    ):
        add_metadata(mock_hugr_node, additional_metadata={"preset-key": "preset-value"})


def test_add_metadata_property_max_qubits():
    mock_hugr_node = Mock()
    mock_hugr_node.metadata = {}

    guppy_metadata = GuppyMetadata()
    guppy_metadata.max_qubits.value = 5
    add_metadata(mock_hugr_node, guppy_metadata)

    assert mock_hugr_node.metadata == {"tket.hint.max_qubits": 5}
