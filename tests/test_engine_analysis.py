"""Lifecycle tests for the engine's finalized graph and modifier information."""

from copy import deepcopy

import pytest
from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.builtins import control, nat
from guppylang.std.quantum import qubit
from guppylang_internals import engine as engine_module
from guppylang_internals.engine import ENGINE


@pytest.fixture
def custom_main():
    @guppy.unitary
    class custom_gate:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
            pass

    @guppy
    def main(q: qubit, c: qubit) -> None:
        with control(c):
            custom_gate(q)

    return main


def test_analysis_is_published_after_custom_specializations_are_checked(
    custom_main, monkeypatch
):
    analyze = engine_module.analyze_modifier_calls
    analysis_passes = 0
    checking_snapshots = []

    def analyze_before_publication(*args, **kwargs):
        nonlocal analysis_passes
        assert ENGINE.analyzed_graph is None
        analysis_passes += 1
        checking_snapshots.append(deepcopy(ENGINE.analysis_cache))
        return analyze(*args, **kwargs)

    monkeypatch.setattr(
        engine_module, "analyze_modifier_calls", analyze_before_publication
    )
    custom_main.check()

    assert analysis_passes >= 2
    assert ENGINE.analysis_cache == checking_snapshots[-1]
    assert ENGINE.analyzed_graph is not None
    [custom_use] = ENGINE.analyzed_graph.custom_uses_by_mono_def.values()
    assert custom_use.custom_def in ENGINE.checked
    assert custom_use.custom_def in ENGINE.call_graph
    assert custom_use.custom_def in ENGINE.load_graph
    assert custom_use.custom_def in ENGINE.analyzed_graph.call_graph
    assert custom_use.custom_def in ENGINE.analyzed_graph.load_graph
    assert ENGINE.call_graph[custom_main.id, ()] == [custom_use.unmodified_callee]
    assert ENGINE.analyzed_graph.call_graph[custom_main.id, ()] == (
        custom_use.custom_def,
    )


@pytest.mark.parametrize("reset", [False, True])
def test_repeated_check_preserves_custom_resolution(custom_main, reset):
    custom_main.check()
    previous_graph = ENGINE.analyzed_graph
    assert previous_graph is not None
    assert previous_graph.custom_uses_by_mono_def
    previous_cache = ENGINE.analysis_cache
    original_checking_data = deepcopy(previous_cache)

    for _ in range(2):
        ENGINE.check([custom_main.id], reset=reset)

        assert ENGINE.analyzed_graph is not None
        assert ENGINE.analyzed_graph is not previous_graph
        assert ENGINE.analyzed_graph == previous_graph
        assert ENGINE.analysis_cache == original_checking_data
        if reset:
            assert ENGINE.analysis_cache is not previous_cache
        else:
            assert ENGINE.analysis_cache is previous_cache
        previous_cache = ENGINE.analysis_cache
        previous_graph = ENGINE.analyzed_graph


def test_reset_clears_analyzed_state(custom_main):
    custom_main.check()
    assert ENGINE.analyzed_graph is not None
    assert ENGINE.analyzed_graph.custom_uses_by_mono_def
    previous_cache = ENGINE.analysis_cache

    ENGINE.reset()

    assert ENGINE.analyzed_graph is None
    assert ENGINE.analysis_cache is not previous_cache
    assert ENGINE.analysis_cache.call_graph == {}
    assert ENGINE.analysis_cache.load_graph == {}
    assert ENGINE.analysis_cache.func_effects == {}
    assert ENGINE.analysis_cache.local_modifiers_by_edge == {}


@pytest.mark.parametrize("reset", [False, True])
def test_interrupted_check_does_not_retain_previous_analysis(
    custom_main, monkeypatch, reset
):
    custom_main.check()
    assert ENGINE.analyzed_graph is not None
    assert ENGINE.analyzed_graph.custom_uses_by_mono_def

    def interrupt_check():
        assert ENGINE.analyzed_graph is None
        raise RuntimeError("interrupted checking")

    monkeypatch.setattr(ENGINE, "_drain_check_worklists", interrupt_check)
    with pytest.raises(RuntimeError, match="interrupted checking"):
        ENGINE.check([custom_main.id], reset=reset)

    assert ENGINE.analyzed_graph is None


def test_additional_check_refreshes_analysis(custom_main):
    custom_main.check()
    previous_graph = ENGINE.analyzed_graph
    assert previous_graph is not None
    assert previous_graph.custom_uses_by_mono_def

    @guppy
    def additional() -> None:
        pass

    ENGINE.get_checked(additional.id, ())

    assert (additional.id, ()) in ENGINE.checked
    assert ENGINE.analyzed_graph is previous_graph
    assert (additional.id, ()) not in previous_graph.call_graph

    ENGINE.check([additional.id], reset=False)

    assert ENGINE.analyzed_graph is not None
    assert ENGINE.analyzed_graph is not previous_graph
    assert (additional.id, ()) in ENGINE.analyzed_graph.call_graph
