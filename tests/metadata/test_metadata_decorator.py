import pytest
from guppylang.decorator import guppy, metadata
from guppylang_internals.error import GuppyError
from guppylang_internals.metadata.common import ReservedMetadataKeysError
from hugr.ops import FuncDefn


def test_metadata_decorator_adds_function_metadata():
    @guppy
    @metadata("test-key", {"nested": ["value"]})
    def foo() -> None:
        pass

    hugr = foo.compile_function().modules[0]
    funcs = [
        data
        for _, data in hugr.nodes()
        if isinstance(data.op, FuncDefn) and data.op.f_name.endswith(".foo")
    ]

    assert len(funcs) == 1
    assert funcs[0].metadata["test-key"] == {"nested": ["value"]}


def test_wrapping_metadata_decorator():

    def custom_metadata(value: str):
        return metadata("custom-key", value)

    @guppy
    @custom_metadata({"nested": ["value"]})
    def main() -> None:
        pass

    hugr = main.compile_function().modules[0]
    funcs = [
        data
        for _, data in hugr.nodes()
        if isinstance(data.op, FuncDefn) and data.op.f_name.endswith(".main")
    ]

    assert len(funcs) == 1
    assert funcs[0].metadata["custom-key"] == {"nested": ["value"]}


def test_metadata_reserved_keys_using_decorator():
    with pytest.raises(
        GuppyError,
        check=lambda e: (
            isinstance(e.error, ReservedMetadataKeysError)
            and e.error.keys == {"tket.unitary"}
        ),
    ):

        @guppy
        @metadata("tket.unitary", "value2")
        def main() -> None:
            pass
