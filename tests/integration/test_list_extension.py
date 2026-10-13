import hashlib
from importlib.resources import files

import pytest
from selene_hugr_qis_compiler import HugrReadError
from hugr import ops
from hugr import tys as ht
from hugr.build.function import Module
from hugr.package import Package
from hugr.std.int import INT_T, IntVal
from hugr.std.collections.array import Array

from guppylang import guppy, qubit
from guppylang.std.array import array
from guppylang.std.lang import owned
from guppylang_internals.error import GuppyError, InternalGuppyError
from guppylang_internals.decorator import custom_type
from guppylang_internals.compiler.core import insert_drops
from guppylang_internals.std._internal.compiler import list_extension
from guppylang_internals.std._internal.compiler.list import (
    list_discard_empty,
    list_get,
    list_insert,
    list_length,
    list_new_op,
    list_pop,
    list_push,
    list_set,
)
from guppylang_internals.std._internal.compiler.list_extension import List, ListVal


@pytest.fixture(autouse=True)
def enable_lists(use_experimental_features):
    pass


def list_ops(package):
    h = package.modules[0]
    return [
        op.op_def().name
        for node in h
        if isinstance(op := h[node].op, ops.ExtOp)
        and op.op_def().qualified_name().startswith("collections.list.")
    ]


def test_artifact_and_python_wrapper():
    artifact = files(list_extension.__package__).joinpath("list_extension.json")
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == (
        "8d51451d03274fdddbdd109a3aeedcd50bc02e8b82e8e8027b71d8fafb32da72"
    )
    assert str(list_extension.EXTENSION.version) == "0.2.0"
    assert List(INT_T).type_bound() == ht.TypeBound.Linear
    assert List(ht.Qubit).type_bound() == ht.TypeBound.Linear
    payload = ListVal([IntVal(1)], INT_T).to_value().val
    assert isinstance(payload, list)
    assert len(payload) == 2


@pytest.mark.parametrize("elem_ty", [INT_T, ht.Qubit, List(INT_T)])
@pytest.mark.parametrize(
    "make_op",
    [
        list_new_op,
        list_pop,
        list_push,
        list_set,
        list_insert,
        list_length,
        list_discard_empty,
    ],
)
def test_signatures(elem_ty, make_op, validate):
    op, _ = make_op(elem_ty)
    sig = op.outer_signature()
    module = Module()
    function = module.define_function("test", sig.input, sig.output)
    result = function.add_op(op, *function.inputs())
    function.set_outputs(*result)
    validate(Package([module.hugr]))


def test_get_signature(validate):
    op, _ = list_get(INT_T)
    assert op.outer_signature().output == [List(INT_T), ht.Option(INT_T)]
    module = Module()
    function = module.define_function("test", [List(INT_T), ht.USize()])
    function.set_outputs(*function.add_op(op, *function.inputs()))
    validate(Package([module.hugr]))
    with pytest.raises(InternalGuppyError, match="copyable"):
        list_get(ht.Qubit)
    with pytest.raises(InternalGuppyError, match="copyable"):
        list_get(List(INT_T))


def test_insert_success_row():
    op, _ = list_insert(ht.Qubit)
    assert op.outer_signature().output == [List(ht.Qubit), ht.Either([ht.Qubit], [])]


def test_empty_linear_disposal(validate):
    @guppy
    def empty() -> None:
        xs: list[qubit] = []
        xs.discard_empty()

    package = empty.compile_function()
    assert list_ops(package) == ["new", "discard_empty"]
    validate(package)


def test_get_threads_handle(validate):
    @guppy
    def access(xs: list[int]) -> int:
        x = xs[0]
        xs.append(x)
        return len(xs)

    package = access.compile_function()
    assert "get" in list_ops(package)
    validate(package)


def test_drop_populated_and_nested_lists(validate):
    @guppy
    def drop() -> None:
        xs = [[1, 2], [3]]
        xs.append([4, 5])

    package = drop.compile_function()
    names = list_ops(package)
    assert names.count("pop") == 2
    assert names.count("discard_empty") == 2
    validate(package)


def test_drop_lists_in_arrays(validate):
    @guppy
    def drop(xs: array[list[int], 2] @ owned) -> None:
        pass

    package = drop.compile_function()
    assert "pop" in list_ops(package)
    assert "discard_empty" in list_ops(package)
    validate(package)


def test_drop_lists_in_branches(validate):
    @guppy
    def branch(b: bool) -> int:
        xs = [1, 2]
        if b:
            return xs.pop()
        return 0

    validate(branch.compile_function())


def test_nested_indexing_requires_copyable_elements():
    @guppy
    def move(xs: list[list[int]] @ owned) -> list[list[int]]:
        xs[0].append(2)
        return xs

    with pytest.raises(GuppyError, match="copyable"):
        move.check()


def test_replace_droppable_noncopyable_element(validate):
    @guppy
    def replace(xs: list[list[int]]) -> None:
        xs.__setitem__(0, [3, 4])

    package = replace.compile_function()
    names = list_ops(package)
    assert "set" in names
    assert "pop" in names
    assert "discard_empty" in names
    validate(package)


def test_drop_array_with_moved_out_slot(validate):
    @guppy
    def move(xs: array[list[int], 2] @ owned) -> list[int]:
        ys = xs.__getitem__(0)
        return ys

    validate(move.compile_function())


def test_empty_disposal_after_pop(validate):
    @guppy
    def pop(xs: list[qubit] @ owned) -> qubit:
        q = xs.pop()
        xs.discard_empty()
        return q

    package = pop.compile_function()
    h = package.modules[0]
    for node in h:
        op = h[node].op
        if isinstance(op, ops.ExtOp) and op.op_def().qualified_name().startswith(
            "collections.list."
        ):
            assert op.args == [ht.TypeTypeArg(ht.Qubit)]
    validate(package)


@pytest.mark.parametrize("ty", [ht.Option(List(INT_T)), Array(List(INT_T), 2)])
def test_drop_aggregate(ty, validate):
    module = Module()
    function = module.define_function("test", [ty], [])
    function.set_outputs()
    insert_drops(module.hugr)
    package = Package([module.hugr])
    assert "pop" in list_ops(package)
    validate(package)


def test_validator_rejects_superseded_get(validate):
    definition = list_extension.EXTENSION.get_op("get")
    op = definition.instantiate(
        [ht.TypeTypeArg(INT_T)],
        ht.FunctionType([List(INT_T), ht.USize()], [ht.Option(INT_T)]),
    )
    module = Module()
    function = module.define_function("test", op.outer_signature().input)
    function.set_outputs(*function.add_op(op, *function.inputs()))
    with pytest.raises((AssertionError, HugrReadError), match=r"signature|Signature"):
        validate(Package([module.hugr]), export=False)


def test_iterator_disposes_exhausted_handle(validate):
    @guppy
    def iterate(xs: list[int] @ owned) -> int:
        result = 0
        for x in xs:
            result = 10 * result + x
        return result

    package = iterate.compile_function()
    names = list_ops(package)
    assert "new" in names
    assert "push" in names
    assert names.count("discard_empty") >= 2
    validate(package)


def test_iteration_literal_graph(validate):
    """Export a no-argument runtime acceptance case whose result should be 123."""

    @guppy
    def iterate() -> int:
        xs = [1, 2, 3]
        result = 0
        for x in xs:
            result = 10 * result + x
        return result

    validate(iterate.compile_function())


def test_noncopyable_element_with_copyable_representation(validate):
    @custom_type(ht.Unit, copyable=False, droppable=False)
    class Token:
        pass

    @guppy
    def singleton(x: Token @ owned) -> list[Token]:
        return [x]

    validate(singleton.compile_function())


def test_swap_returns_direct_linear_element(validate):
    @guppy
    def swap(xs: list[qubit], q: qubit @ owned) -> qubit:
        return xs.swap(0, q)

    package = swap.compile_function()
    h = package.modules[0]
    sets = [
        h[node].op
        for node in h
        if isinstance(h[node].op, ops.ExtOp)
        and h[node].op.op_def().qualified_name() == "collections.list.set"
    ]
    assert len(sets) == 1
    assert sets[0].outer_signature().output == [
        List(ht.Qubit),
        ht.Either([ht.Qubit], [ht.Qubit]),
    ]
    validate(package)
