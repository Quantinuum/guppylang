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
