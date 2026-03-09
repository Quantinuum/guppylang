from guppylang.std import array
from guppylang.std.debug import state_result
from guppylang.std.quantum import discard, discard_array, qubit
from guppylang_internals.debug_mode import turn_off_debug_mode, turn_on_debug_mode
from guppylang_internals.metadata.debug_info import (
    DICompileUnit,
    DILocation,
    DISubprogram,
    HugrDebugInfo,
)
from hugr.ops import Call, ExtOp, FuncDecl, FuncDefn, MakeTuple

from guppylang import guppy
from tests.resources.metadata_example import (
    bar,
    baz,
    comptime_bar,
    pytket_bar_load,
    pytket_bar_stub,
)

turn_on_debug_mode()


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
        comptime_bar()
        q = qubit()
        pytket_bar_load(q)
        pytket_bar_stub(q)
        discard(q)

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
                assert debug_info.line_no == 45
                assert debug_info.scope_line == 46
            case "bar":
                assert HugrDebugInfo in func.metadata
                debug_info = DISubprogram.from_json(func.metadata[HugrDebugInfo.KEY])
                assert debug_info.file == 1
                assert debug_info.line_no == 10
                assert debug_info.scope_line == 13
            case "baz":
                assert HugrDebugInfo in func.metadata
                debug_info = DISubprogram.from_json(func.metadata[HugrDebugInfo.KEY])
                assert debug_info.file == 1
                assert debug_info.line_no == 17
                assert debug_info.scope_line is None
            case "comptime_bar":
                assert HugrDebugInfo in func.metadata
                debug_info = DISubprogram.from_json(func.metadata[HugrDebugInfo.KEY])
                assert debug_info.file == 1
                assert debug_info.line_no == 21
                assert debug_info.scope_line == 22
            case "pytket_bar_load":
                assert HugrDebugInfo in func.metadata
                debug_info = DISubprogram.from_json(func.metadata[HugrDebugInfo.KEY])
                assert debug_info.file == 1
                assert debug_info.line_no == 28
                assert debug_info.scope_line is None
            case "pytket_bar_stub":
                assert HugrDebugInfo in func.metadata
                debug_info = DISubprogram.from_json(func.metadata[HugrDebugInfo.KEY])
                assert debug_info.file == 1
                assert debug_info.line_no == 32
                assert debug_info.scope_line is None
            case "":
                # No metadata on the inner circuit function.
                assert HugrDebugInfo not in func.metadata
            case _:
                raise AssertionError(f"Unexpected function name {op.f_name}")


def test_call_location():
    @guppy
    def foo() -> None:
        bar()  # call 1
        comptime_bar()  # call 2
        q = qubit()  # compiles to extension op (see test below)
        pytket_bar_load(q)  # call 3 + inner circuit function call 4
        discard(q)  # compiles to extension op (see test below)

    hugr = foo.compile().modules[0]
    calls = [node for node, node_data in hugr.nodes() if isinstance(node_data.op, Call)]
    assert len(calls) == 4
    lines = []
    for call in calls:
        assert HugrDebugInfo in call.metadata
        debug_info = DILocation.from_json(call.metadata[HugrDebugInfo.KEY])
        if debug_info.line_no == 28:
            assert debug_info.column == 0
        else:
            assert debug_info.column == 8
        lines.append(debug_info.line_no)
    assert lines == [113, 114, 28, 116]


# TODO: Improve this test.
def test_ext_op_location():
    @guppy.struct
    class MyStruct:
        x: int

    @guppy
    def foo() -> None:
        MyStruct(1)  # Defined through `custom_function` (`MakeTuple` node)
        q = qubit()  # Defined through `hugr_op`
        arr = array(q)  # Forces the use of various array extension ops
        state_result("tag", arr)  # Defined through `custom_function` (custom node)
        discard_array(arr)  # Defined through `hugr_op`

    hugr = foo.compile().modules[0]
    # TODO: Figure out how to attach metadata to these nodes.
    # TODO: Find other such limitations and add tests for them.
    known_limitations = [
        "tket.bool.read",
        "prelude.panic<[Type(Tuple(int<6>, Tuple(int<6>, int<6>, int<6>)))], []>",
        "prelude.panic<[], [Type(Tuple(int<6>, Tuple(int<6>, int<6>, int<6>)))]>",
    ]
    found_annotated_tuples = []
    for node, node_data in hugr.nodes():
        if (
            isinstance(node_data.op, ExtOp)
            and node_data.op.name() not in known_limitations
        ):
            assert HugrDebugInfo in node.metadata
            debug_info = DILocation.from_json(node.metadata[HugrDebugInfo.KEY])
        # Check constructor is annotated.
        if isinstance(node_data.op, MakeTuple) and HugrDebugInfo in node.metadata:
            debug_info = DILocation.from_json(node.metadata[HugrDebugInfo.KEY])
            found_annotated_tuples.append(debug_info.line_no)
    assert 142 in found_annotated_tuples


def test_turn_off_debug_mode():
    turn_off_debug_mode()

    @guppy
    def foo() -> None:
        q = qubit()
        state_result("tag", q)
        discard(q)

    hugr = foo.compile().modules[0]
    for node, _ in hugr.nodes():
        assert HugrDebugInfo not in node.metadata
