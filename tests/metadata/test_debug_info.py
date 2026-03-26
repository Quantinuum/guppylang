from pathlib import Path
from typing import TYPE_CHECKING

from guppylang import guppy
from guppylang.std import array
from guppylang.std.debug import state_result
from guppylang.std.lang import comptime
from guppylang.std.platform import result
from guppylang.std.quantum import discard, discard_array, qubit
from guppylang_internals.debug_mode import turn_off_debug_mode, turn_on_debug_mode
from hugr.debug_info import DICompileUnit, DILocation, DISubprogram
from hugr.metadata import HugrDebugInfo
from hugr.ops import Call, ExtOp, FuncDecl, FuncDefn, MakeTuple

from tests.resources.debug_info_example import (
    bar,
    baz,
    comptime_bar,
    pytket_bar_load,
    pytket_bar_stub,
)

if TYPE_CHECKING:
    from hugr import Node

turn_on_debug_mode()


def get_last_uri_part(uri: str) -> str:
    return uri.split("/")[-1]


def get_last_name_part(file_name: str) -> str:
    return file_name.split(".")[-1]


def test_compile_unit():
    @guppy
    def foo() -> None:
        pass

    hugr = foo.compile().modules[0]
    meta = hugr.module_root.metadata
    assert HugrDebugInfo in meta
    debug_info = DICompileUnit.from_json(meta[HugrDebugInfo.KEY])
    assert debug_info.directory == Path.cwd().as_uri()
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
        "debug_info_example.py",
    ]

    funcs = hugr.children(hugr.module_root)
    func_map: dict[str, Node] = {}
    for func in funcs:
        op = hugr[func].op
        assert isinstance(op, FuncDefn | FuncDecl)
        func_map[get_last_name_part(op.f_name)] = func

    foo_func = func_map.pop("foo")
    assert HugrDebugInfo in foo_func.metadata
    debug_info = DISubprogram.from_json(foo_func.metadata[HugrDebugInfo.KEY])
    assert debug_info.file == 0
    assert debug_info.line_no == 53
    assert debug_info.scope_line == 54

    bar_func = func_map.pop("bar")
    assert HugrDebugInfo in bar_func.metadata
    debug_info = DISubprogram.from_json(bar_func.metadata[HugrDebugInfo.KEY])
    assert debug_info.file == 1
    assert debug_info.line_no == 9
    assert debug_info.scope_line == 12

    baz_func = func_map.pop("baz")
    assert HugrDebugInfo in baz_func.metadata
    debug_info = DISubprogram.from_json(baz_func.metadata[HugrDebugInfo.KEY])
    assert debug_info.file == 1
    assert debug_info.line_no == 16
    assert debug_info.scope_line is None

    comptime_bar_func = func_map.pop("comptime_bar")
    assert HugrDebugInfo in comptime_bar_func.metadata
    debug_info = DISubprogram.from_json(comptime_bar_func.metadata[HugrDebugInfo.KEY])
    assert debug_info.file == 1
    assert debug_info.line_no == 20
    assert debug_info.scope_line == 21

    pytket_bar_load_func = func_map.pop("pytket_bar_load")
    assert HugrDebugInfo in pytket_bar_load_func.metadata
    debug_info = DISubprogram.from_json(
        pytket_bar_load_func.metadata[HugrDebugInfo.KEY]
    )
    assert debug_info.file == 1
    assert debug_info.line_no == 27
    assert debug_info.scope_line is None

    pytket_bar_stub_func = func_map.pop("pytket_bar_stub")
    assert HugrDebugInfo in pytket_bar_stub_func.metadata
    debug_info = DISubprogram.from_json(
        pytket_bar_stub_func.metadata[HugrDebugInfo.KEY]
    )
    assert debug_info.file == 1
    assert debug_info.line_no == 31
    assert debug_info.scope_line is None

    inner_func = func_map.pop("")
    # No metadata on the inner circuit function.
    assert HugrDebugInfo not in inner_func.metadata

    assert len(func_map) == 0


def test_call_location():
    @guppy
    def foo() -> None:
        bar()  # call 1
        comptime_bar()  # call 2
        q = qubit()  # compiles to extension op (see test below)
        pytket_bar_load(q)  # inner circuit function call 3 (in other file) + call 4
        discard(q)  # compiles to extension op (see test below)

    hugr = foo.compile().modules[0]
    calls = [node for node, node_data in hugr.nodes() if isinstance(node_data.op, Call)]
    assert len(calls) == 4
    expected_info = [(134, 8), (135, 8), (27, 0), (137, 8)]
    for i, call in enumerate(calls):
        assert HugrDebugInfo in call.metadata
        debug_info = DILocation.from_json(call.metadata[HugrDebugInfo.KEY])
        assert (debug_info.line_no, debug_info.column) == expected_info[i]


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
        numbers = comptime([1, 2, 3])  # Checks frozenarray usage
        x = numbers[0]  # Checks frozenarray usage
        bools = array(True, False)  # Checks general array usage
        bools[1] = True
        count = 2
        while count > x:  # Check inside of control flow
            count -= 1
            for _ in range(2):
                if bools[0]:
                    result("tag", bools)  # Check result usage

    hugr = foo.compile().modules[0]

    known_exceptions = [
        # TODO: Reads are usually used inside of a global function defined by a compiler
        # extension where we currently cannot attach debug info.
        "tket.bool.read",
        "tket.guppy.drop",
    ]
    found_annotated_tuples = []
    for node, node_data in hugr.nodes():
        if isinstance(node_data.op, ExtOp) and not any(
            exception in node_data.op.name() for exception in known_exceptions
        ):
            assert HugrDebugInfo in node.metadata
            debug_info = DILocation.from_json(node.metadata[HugrDebugInfo.KEY])
        if isinstance(node_data.op, MakeTuple) and HugrDebugInfo in node.metadata:
            debug_info = DILocation.from_json(node.metadata[HugrDebugInfo.KEY])
            found_annotated_tuples.append(debug_info.line_no)
    # Check constructor call is annotated (even though it is not an ExtOp).
    assert 157 in found_annotated_tuples


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
