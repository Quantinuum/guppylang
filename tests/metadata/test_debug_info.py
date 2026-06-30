import ast
import inspect
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

from guppylang import guppy
from guppylang.std import array
from guppylang.std.debug import state_output
from guppylang.std.lang import comptime
from guppylang.std.platform import output
from guppylang.std.quantum import discard, discard_array, qubit
from guppylang_internals.debug_mode import turn_off_debug_mode, turn_on_debug_mode
from hugr.debug_info import DICompileUnit, DILocation, DISubprogram
from hugr.metadata import HugrDebugInfo
from hugr.ops import Call, ExtOp, FuncDecl, FuncDefn, MakeTuple

from tests.resources import debug_info_example
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


def definition_ast(definition) -> ast.FunctionDef:
    """Parse a Guppy definition's Python source with original line/column positions."""
    lines, line_offset = inspect.getsourcelines(definition.wrapped.python_func)
    source = "".join(lines)
    if lines[0][0].isspace():
        tree = ast.parse(f"if True:\n{source}")
        [node] = tree.body[0].body
        ast.increment_lineno(node, line_offset - 2)
    else:
        tree = ast.parse(source)
        [node] = tree.body
        ast.increment_lineno(node, line_offset - 1)
    assert isinstance(node, ast.FunctionDef)
    return node


def module_assignment_location(module: ModuleType, target_name: str) -> tuple[int, int]:
    """Return the source location of a module-level assignment."""
    lines, line_offset = inspect.getsourcelines(module)
    line_offset = max(line_offset, 1)
    tree = ast.parse("".join(lines))
    assignment = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == target_name
            for target in node.targets
        )
    )
    return line_offset + assignment.lineno - 1, assignment.col_offset


def call_location(definition, call_name: str) -> tuple[int, int]:
    function = definition_ast(definition)
    call = next(
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == call_name
    )
    return call.lineno, call.col_offset


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

    def check_subprogram(name, file_idx, definition, *, is_decl=False):
        node = definition_ast(definition)
        func = func_map.pop(name)
        assert HugrDebugInfo in func.metadata
        debug_info = DISubprogram.from_json(func.metadata[HugrDebugInfo.KEY])
        assert debug_info.file == file_idx
        assert (debug_info.line_no, debug_info.scope_line) == (
            node.lineno,
            None if is_decl else node.body[0].lineno,
        )

    check_subprogram("foo", 0, foo)
    check_subprogram("bar", 1, bar)
    check_subprogram("baz", 1, baz, is_decl=True)
    check_subprogram("comptime_bar", 1, comptime_bar)

    pytket_bar_load_func = func_map.pop("pytket_bar_load")
    assert HugrDebugInfo in pytket_bar_load_func.metadata
    subprogram = DISubprogram.from_json(
        pytket_bar_load_func.metadata[HugrDebugInfo.KEY]
    )
    assert subprogram.file == 1
    assert (
        subprogram.line_no
        == module_assignment_location(debug_info_example, "pytket_bar_load")[0]
    )
    assert subprogram.scope_line is None

    check_subprogram("pytket_bar_stub", 1, pytket_bar_stub, is_decl=True)

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
    expected_info = [
        call_location(foo, "bar"),
        call_location(foo, "comptime_bar"),
        module_assignment_location(debug_info_example, "pytket_bar_load"),
        call_location(foo, "pytket_bar_load"),
    ]
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
        state_output("tag", arr)  # Defined through `custom_function` (custom node)
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
                    output("tag", bools)  # Check output usage

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
    assert call_location(foo, "MyStruct")[0] in found_annotated_tuples


def test_turn_off_debug_mode():
    turn_off_debug_mode()

    @guppy
    def foo() -> None:
        q = qubit()
        state_output("tag", q)
        discard(q)

    hugr = foo.compile().modules[0]
    for node, _ in hugr.nodes():
        assert HugrDebugInfo not in node.metadata
