"""Integration tests for modifier-labelled call-graph analysis."""

import pytest
from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.builtins import (
    Controllable,
    Function,
    Unitary,
    control,
    dagger,
    nat,
    panic,
)
from guppylang.std.quantum import discard, measure, qubit, x
from guppylang_internals.analysis.callgraph import CallGraph
from guppylang_internals.analysis.effects import compute_effects
from guppylang_internals.checker.modifier import (
    NO_CALL_MODIFIERS,
    CustomModifierKind,
)
from guppylang_internals.engine import ENGINE
from guppylang_internals.tys import Effect
from guppylang_internals.tys.arg import ConstArg
from guppylang_internals.tys.builtin import nat_type
from guppylang_internals.tys.const import ConstValue


@guppy.unitary
class _same_count_recursive_gate:
    @guppy
    def __call__(q: qubit) -> None:
        pass

    @guppy
    def controlled[n: nat](q: qubit, controls: array[qubit, n]) -> None:
        _same_count_helper(q, controls)


@guppy
def _same_count_helper[n: nat](q: qubit, controls: array[qubit, n]) -> None:
    with control(controls):
        _same_count_recursive_gate(q)


def test_effects_after_custom_modifier_resolution_is_removed():
    """
    Effects are propagated through custom modifier calls:

    We check that after updating the call graph with custom modifier resolution,
    the effects in `__call__` is not included in the effects of `custom_main`.
    """

    @guppy.unitary
    class custom_gate:
        @guppy
        def __call__(q: qubit) -> None:
            panic("parent effect")

        @guppy
        def controlled[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
            pass

    @guppy
    def fallback() -> None:
        panic("fallback effect")

    @guppy
    def custom_main(q: qubit, c: qubit) -> None:
        with control(c):
            custom_gate(q)

    custom_main.check()
    effects = compute_effects(CallGraph(ENGINE.call_graph), ENGINE.func_effects)
    [custom_use] = ENGINE.custom_uses_by_mono_def.values()
    assert effects[custom_use.unmodified_callee] == frozenset({Effect.ANY})
    assert effects[custom_use.custom_def] == frozenset()
    assert effects[custom_main.id, ()] == frozenset()


def test_effects_after_custom_modifier_resolution_is_added():
    """
    Effects are propagated through custom modifier calls:

    We check that after updating the call graph with custom modifier resolution,
    `main` includes the effects of the controlled version of `custom_gate`.
    """

    @guppy.unitary
    class custom_gate:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled[n: nat](q: qubit, controls: array[qubit, n]) -> None:
            panic("custom effect")

    @guppy
    def main(q: qubit, c: qubit) -> None:
        with control(c):
            custom_gate(q)

    main.check()
    [custom_use] = ENGINE.custom_uses_by_mono_def.values()
    effects = compute_effects(CallGraph(ENGINE.call_graph), ENGINE.func_effects)
    assert effects[custom_use.custom_def] == frozenset({Effect.ANY})
    assert effects[main.id, ()] == frozenset({Effect.ANY})


def test_recursive_custom_modifier_same_control_count():
    """Indirect recursion at the same control count reaches a fixed point."""

    @guppy
    def main(q: qubit, c: qubit) -> None:
        with control(c):
            _same_count_recursive_gate(q)

    main.check()

    [custom_use] = ENGINE.custom_uses_by_mono_def.values()
    custom_def = custom_use.custom_def
    helper_instantiation = (
        _same_count_helper.id,
        (ConstArg(ConstValue(nat_type(), 1)),),
    )

    assert custom_use.control_count == 1
    assert helper_instantiation in ENGINE.call_graph[custom_def]
    assert custom_def in ENGINE.call_graph[helper_instantiation]


def test_non_recursive_control_count_increase_is_allowed():
    """Different non-recursive paths may use increasing control counts."""

    @guppy.unitary
    class custom_gate:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
            pass

    @guppy
    def call_with_one_control(q: qubit, c: qubit) -> None:
        with control(c):
            custom_gate(q)

    @guppy
    def call_with_two_controls(q: qubit, controls: array[qubit, 2]) -> None:
        with control(controls):
            custom_gate(q)

    @guppy
    def main(q: qubit, c: qubit, controls: array[qubit, 2]) -> None:
        call_with_one_control(q, c)
        call_with_two_controls(q, controls)

    main.check()

    assert {use.control_count for use in ENGINE.custom_uses_by_mono_def.values()} == {
        1,
        2,
    }


def test_modifier_context_propagates_through_higher_order_and_helper_calls():
    """Control and dagger propagate through higher-order and ordinary helpers."""

    @guppy.unitary
    class custom_gate:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
            pass

        @guppy
        def daggered(q: qubit) -> None:
            pass

        @guppy
        def ctrl_daggered[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
            pass

    @guppy(unitary=True)
    def apply(f: Unitary[[qubit], None], q: qubit) -> None:
        f(q)

    @guppy(unitary=True)
    def helper(q: qubit) -> None:
        custom_gate(q)

    @guppy
    def main(
        apply_controlled_q: qubit,
        apply_daggered_q: qubit,
        helper_controlled_q: qubit,
        helper_daggered_q: qubit,
        control_qubit: qubit,
    ) -> None:
        # Exercise context propagation through a monomorphized higher-order call.
        with control(control_qubit):
            apply(custom_gate, apply_controlled_q)
        with dagger:
            apply(custom_gate, apply_daggered_q)

        # Exercise the same contexts through a regular, non-higher-order helper.
        with control(control_qubit):
            helper(helper_controlled_q)
        with dagger:
            helper(helper_daggered_q)

    main.check()

    # The higher-order argument identifies one concrete apply monomorphization.
    apply_mono = next(
        callee for callee in ENGINE.call_graph[main.id, ()] if callee[0] == apply.id
    )
    helper_mono = (helper.id, ())
    gate_mono = (custom_gate.id, ())
    uses_by_kind = {
        custom_use.kind: custom_use
        for custom_use in ENGINE.custom_uses_by_mono_def.values()
    }
    assert set(uses_by_kind) == {
        CustomModifierKind.CONTROLLED,
        CustomModifierKind.DAGGERED,
    }
    controlled_use = uses_by_kind[CustomModifierKind.CONTROLLED]
    daggered_use = uses_by_kind[CustomModifierKind.DAGGERED]

    # Checking records only the empty contexts local to each helper body.
    assert set(ENGINE.local_modifiers_by_edge[apply_mono, gate_mono]) == {
        NO_CALL_MODIFIERS
    }
    assert set(ENGINE.local_modifiers_by_edge[helper_mono, gate_mono]) == {
        NO_CALL_MODIFIERS
    }

    # Analysis resolves both inherited contexts to the matching custom definitions.
    assert controlled_use.unmodified_callee == gate_mono
    assert controlled_use.control_count == 1
    assert daggered_use.unmodified_callee == gate_mono
    assert daggered_use.control_count is None

    # The projected graph retains the controlled and daggered targets for both paths,
    # without retaining the unmodified gate that neither path calls.
    expected_custom_defs = {controlled_use.custom_def, daggered_use.custom_def}
    assert set(ENGINE.call_graph[apply_mono]) == expected_custom_defs
    assert set(ENGINE.call_graph[helper_mono]) == expected_custom_defs


@pytest.mark.parametrize("comptime", [False, True])
def test_custom_modifier_in_returned_function(comptime, run_int_fn):
    """A function returned by a factory needs its custom implementations (#2343)."""

    @guppy.unitary
    class custom_gate:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
            x(q)

    @guppy
    def loaded(q: qubit, c: qubit) -> None:
        with control(c):
            custom_gate(q)

    factory_decorator = guppy.comptime if comptime else guppy

    @factory_decorator
    def factory() -> Function[[qubit, qubit], None]:
        return loaded

    @guppy
    def main() -> int:
        q = qubit()
        c = qubit()
        x(c)
        f = factory()
        f(q, c)
        result = measure(q).read()
        discard(c)
        return 1 if result else 0

    main.check()
    [custom_use] = ENGINE.custom_uses_by_mono_def.values()
    assert custom_use.control_count == 1
    assert custom_use.custom_def in ENGINE.call_graph[loaded.id, ()]
    assert (loaded.id, ()) not in ENGINE.call_graph[main.id, ()]
    assert (loaded.id, ()) in ENGINE.load_graph[factory.id, ()]
    assert (loaded.id, ()) not in ENGINE.call_graph[factory.id, ()]

    # Only the custom implementation flips q; the generated controlled body is empty.
    run_int_fn(main, expected=1, num_qubits=2)


def test_loaded_function_does_not_inherit_modifiers():
    """Load chains start fresh contexts, then propagate local modifiers to calls."""

    @guppy.unitary
    class custom_gate:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
            pass

        @guppy
        def daggered(q: qubit) -> None:
            pass

        @guppy
        def ctrl_daggered[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
            pass

    @guppy(controllable=True)
    def helper(q: qubit) -> None:
        custom_gate(q)

    @guppy
    def loaded[n: nat](q: qubit, c: qubit) -> None:
        with control(c):
            helper(q)

    @guppy
    def factory() -> Function[[qubit, qubit], None]:
        return loaded[2]

    @guppy(daggerable=True)
    def loader() -> None:
        f = factory

    @guppy
    def main() -> None:
        with dagger:
            loader()

    main.check()
    [custom_use] = ENGINE.custom_uses_by_mono_def.values()
    assert custom_use.kind == CustomModifierKind.CONTROLLED
    assert custom_use.control_count == 1
    assert ENGINE.call_graph[loader.id, ()] == []
    assert ENGINE.call_graph[factory.id, ()] == []
    loaded_mono = (loaded.id, (ConstArg(ConstValue(nat_type(), 2)),))
    assert ENGINE.call_graph[loaded_mono] == [(helper.id, ())]
    assert ENGINE.call_graph[helper.id, ()] == [custom_use.custom_def]


def test_propagated_context_does_not_change_unmodified_invocation():
    """The same callable specialization can be invoked with two contexts."""

    @guppy.unitary
    class custom_gate:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
            pass

    @guppy(controllable=True)
    def apply(f: Controllable[[qubit], None], q: qubit) -> None:
        f(q)

    @guppy
    def main(q1: qubit, q2: qubit, control_qubit: qubit) -> None:
        apply(custom_gate, q1)
        with control(control_qubit):
            apply(custom_gate, q2)

    main.check()

    # Both call sites share the same monomorphized higher-order function.
    [apply_mono] = {
        callee for callee in ENGINE.call_graph[main.id, ()] if callee[0] == apply.id
    }
    [custom_use] = ENGINE.custom_uses_by_mono_def.values()
    gate_mono = (custom_gate.id, ())

    # Projecting contextual states keeps both valid targets: the unmodified invocation
    # reaches __call__, while the controlled invocation reaches controlled[1].
    assert gate_mono in ENGINE.call_graph[apply_mono]
    assert custom_use.custom_def in ENGINE.call_graph[apply_mono]
    # Propagation must not mutate the empty local label checked inside apply.
    assert set(ENGINE.local_modifiers_by_edge[apply_mono, gate_mono]) == {
        NO_CALL_MODIFIERS
    }
