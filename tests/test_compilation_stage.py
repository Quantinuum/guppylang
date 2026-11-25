from copy import deepcopy
from types import SimpleNamespace

import pytest
from guppylang import guppy
from guppylang_internals.checker.modifier import NO_CALL_MODIFIERS
from guppylang_internals.definition.common import DefId
from guppylang_internals.engine import ENGINE, CompilationStage, CompilationStageError
from guppylang_internals.tys import Effect


@pytest.mark.parametrize("mutation", ["load", "call", "effects", "node"])
@pytest.mark.parametrize("stage", list(CompilationStage))
def test_call_info_mutation_rejected_after_analysis(mutation, stage):
    @guppy
    def root() -> int:
        return 42

    root.check()
    assert ENGINE.analyzed_graph is not None
    mono_id = (root.id, ())

    original_info = deepcopy(ENGINE.call_info)
    original_analysis = ENGINE.analyzed_graph
    error = AssertionError if stage == CompilationStage.CHECK else CompilationStageError
    message = (
        "Call information must not change after analysis"
        if stage == CompilationStage.CHECK
        else "update call information"
    )

    def mutate():
        match mutation:
            case "load":
                ENGINE.register_load(mono_id, mono_id)
            case "call":
                callee = ENGINE.get_parsed(root.id)
                ctx = SimpleNamespace(
                    current_caller=mono_id, modifier_ctx=NO_CALL_MODIFIERS
                )
                ENGINE.register_call(ctx, callee, (), callee.defined_at)
            case "effects":
                ENGINE.register_effects(mono_id, [Effect.PANIC])
            case "node":
                ENGINE.register_call_graph_node((DefId.fresh(), ()))

    with ENGINE._in_stage(stage), pytest.raises(error, match=message):
        mutate()

    assert ENGINE.call_info == original_info
    assert ENGINE.analyzed_graph is original_analysis


def test_compilation_rejects_call_info_mutation(monkeypatch):
    from guppylang_internals.compiler.core import CompilerContext

    @guppy
    def root() -> int:
        return 42

    iterate_worklist = CompilerContext.iterate_worklist

    def mutate_after_lowering(ctx):
        # Run normal lowering, then change call information to trigger the guard.
        iterate_worklist(ctx)
        ENGINE.register_effects((root.id, ()), [Effect.PANIC])

    monkeypatch.setattr(CompilerContext, "iterate_worklist", mutate_after_lowering)
    with pytest.raises(CompilationStageError, match="update call information"):
        ENGINE.compile([root.id])
