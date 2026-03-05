from guppylang.std.debug import state_result
from guppylang_internals.metadata.debug_info import (
    DICompileUnit,
    DILocation,
    DISubprogram,
    HugrDebugInfo,
)
from hugr.ops import Call, ExtOp, FuncDecl, FuncDefn

from guppylang import guppy
from guppylang.std.quantum import discard, qubit
from tests.resources.metadata_example import bar, baz


def get_last_uri_part(uri: str) -> str:
    return uri.split("/")[-1]


def test_compile_unit():
    @guppy
    def foo() -> None:
        pass

    hugr = foo.compile().modules[0]
    meta = hugr.module_root.metadata
    assert HugrDebugInfo in meta
    debug_info = DICompileUnit.from_json(meta[HugrDebugInfo.KEY])
    assert get_last_uri_part(debug_info.directory) == "guppylang"
    assert get_last_uri_part(debug_info.file_table[0]) == "test_debug_info.py"
    assert debug_info.filename == 0


def test_subprogram():
    @guppy
    def foo() -> None:
        bar()
        baz()

    hugr = foo.compile().modules[0]
    meta = hugr.module_root.metadata
    assert HugrDebugInfo in meta
    debug_info = DICompileUnit.from_json(meta[HugrDebugInfo.KEY])
    assert [get_last_uri_part(uri) for uri in debug_info.file_table] == [
        "test_debug_info.py",
        "metadata_example.py",
    ]
    funcs = hugr.children(hugr.module_root)
    for func in funcs:
        op = hugr[func].op
        assert isinstance(op, FuncDefn | FuncDecl)
        match op.f_name:
            case "foo":
                assert HugrDebugInfo in func.metadata
                debug_info = DISubprogram.from_json(func.metadata[HugrDebugInfo.KEY])
                assert debug_info.file == 0
                assert debug_info.line_no == 35
                assert debug_info.scope_line == 36
            case "bar":
                assert HugrDebugInfo in func.metadata
                debug_info = DISubprogram.from_json(func.metadata[HugrDebugInfo.KEY])
                assert debug_info.file == 1
                assert debug_info.line_no == 7
                assert debug_info.scope_line == 10
            case "baz":
                assert HugrDebugInfo in func.metadata
                debug_info = DISubprogram.from_json(func.metadata[HugrDebugInfo.KEY])
                assert debug_info.file == 1
                assert debug_info.line_no == 14
                assert debug_info.scope_line is None
            case _:
                raise AssertionError(f"Unexpected function name {op.f_name}")


def test_call_location():
    @guppy
    def foo() -> None:
        bar()

    hugr = foo.compile().modules[0]
    for node, node_data in hugr.nodes():
        if isinstance(node_data.op, Call):
            assert HugrDebugInfo in node.metadata
            debug_info = DILocation.from_json(node.metadata[HugrDebugInfo.KEY])
            assert debug_info.line_no == 77
            assert debug_info.column == 8


def test_custom_function():
    @guppy
    def foo() -> None:
        q = qubit()
        state_result("tag", q)
        discard(q)

    hugr = foo.compile().modules[0]
    for node, node_data in hugr.nodes():
        if isinstance(node_data.op, ExtOp) and "unpack" not in node_data.op.name():
            assert HugrDebugInfo in node.metadata

