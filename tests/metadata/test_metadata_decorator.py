from guppylang.decorator import guppy, metadata
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
