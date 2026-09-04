"""Integration tests for modifier-labelled call-graph analysis."""

from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.builtins import control, dagger, nat, panic
from guppylang.std.quantum import qubit
from guppylang_internals.analysis.callgraph import CallGraph
from guppylang_internals.analysis.effects import compute_effects
from guppylang_internals.checker.modifier import CustomModifierKind
from guppylang_internals.engine import ENGINE
from guppylang_internals.tys import Effect
from guppylang_internals.tys.arg import ConstArg
from guppylang_internals.tys.builtin import nat_type
from guppylang_internals.tys.const import ConstValue


@guppy.unitary
class _same_count_recursive_gate:
    n = guppy.nat_var("n")

    @guppy
    def __call__(q: qubit) -> None:
        pass

    @guppy
    def controlled(q: qubit, controls: array[qubit, n]) -> None:
        _same_count_helper(q, controls)


@guppy
def _same_count_helper[n: nat](q: qubit, controls: array[qubit, n]) -> None:
    with control(controls):
        _same_count_recursive_gate(q)


def test_custom_modifier_effects_use_expanded_call_graph(
    use_experimental_features,
):
    """Effects follow a custom target, while ordinary calls keep their target."""

    @guppy.unitary
    class custom_gate:
        n = guppy.nat_var("n")

        @guppy
        def __call__(q: qubit) -> None:
            panic("parent effect")

        @guppy
        def controlled(q: qubit, _controls: array[qubit, n]) -> None:
            pass

    @guppy
    def fallback() -> None:
        panic("fallback effect")

    @guppy
    def custom_main(q: qubit, c: qubit) -> None:
        with control(c):
            custom_gate(q)

    @guppy
    def fallback_main() -> None:
        fallback()

    ENGINE.check([custom_main.id, fallback_main.id])
    effects = compute_effects(CallGraph(ENGINE.call_graph), ENGINE.func_effects)

    [custom_use] = ENGINE.custom_uses_by_mono_def.values()
    assert effects[custom_use.unmodified_callee] == frozenset({Effect.ANY})
    assert effects[custom_use.custom_def] == frozenset()
    assert effects[custom_main.id, ()] == frozenset()
    assert effects[fallback_main.id, ()] == frozenset({Effect.ANY})


def test_recursive_custom_modifier_effects(use_experimental_features):
    """Recursive custom definitions participate in effect SCC analysis."""

    @guppy.unitary
    class recursive_gate:
        n = guppy.nat_var("n")

        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled(q: qubit, controls: array[qubit, n]) -> None:
            panic("recursive custom effect")

    @guppy
    def main(q: qubit, c: qubit) -> None:
        with control(c):
            recursive_gate(q)

    main.check()
    [custom_use] = ENGINE.custom_uses_by_mono_def.values()
    custom_def = custom_use.custom_def
    # Model recursion on the concrete custom definition. A unitary class cannot
    # currently refer to its enclosing class name from inside the class-body frame.
    ENGINE.call_graph[custom_def].append(custom_def)

    effects = compute_effects(CallGraph(ENGINE.call_graph), ENGINE.func_effects)
    assert custom_def in ENGINE.call_graph[custom_def]
    assert effects[custom_def] == frozenset({Effect.ANY})
    assert effects[main.id, ()] == frozenset({Effect.ANY})


def test_recursive_custom_modifier_same_control_count(use_experimental_features):
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


def test_non_recursive_control_count_increase_is_allowed(use_experimental_features):
    """Different non-recursive paths may use increasing control counts."""

    @guppy.unitary
    class custom_gate:
        n = guppy.nat_var("n")

        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled(q: qubit, _controls: array[qubit, n]) -> None:
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


def test_expanded_edges_replace_unmodified_callee(use_experimental_features):
    @guppy.unitary
    class custom_gate:
        n = guppy.nat_var("n")

        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def daggered(q: qubit) -> None:
            pass

        @guppy
        def controlled(q: qubit, _controls: array[qubit, n]) -> None:
            pass

        @guppy
        def ctrl_daggered(q: qubit, _controls: array[qubit, n]) -> None:
            pass

    @guppy
    def main(q: qubit, control_qubit: qubit) -> None:
        with dagger:
            custom_gate(q)
        with control(control_qubit):
            custom_gate(q)
        with control(control_qubit), dagger:
            custom_gate(q)

    main.check()

    resolved_custom_defs = {
        custom_use.custom_def for custom_use in ENGINE.custom_uses_by_mono_def.values()
    }
    assert {use.kind for use in ENGINE.custom_uses_by_mono_def.values()} == set(
        CustomModifierKind
    )
    assert resolved_custom_defs <= set(ENGINE.call_graph[main.id, ()])
    assert (custom_gate.id, ()) not in ENGINE.call_graph[main.id, ()]
