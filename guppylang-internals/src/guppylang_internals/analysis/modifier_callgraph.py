"""Context-sensitive propagation and resolution of call modifiers."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from guppylang_internals.checker.errors.generic import (
    RecursiveModifierControlCountError,
)
from guppylang_internals.checker.modifier import (
    NO_CALL_MODIFIERS,
    CustomModifierKind,
    ModifierContext,
)
from guppylang_internals.definition.common import DefId
from guppylang_internals.error import GuppyError
from guppylang_internals.tys.subst import Inst, is_concrete_inst

if TYPE_CHECKING:
    from guppylang_internals.ast_util import AstNode


MonoDefId = tuple[DefId, Inst]
CallGraphEdge = tuple[MonoDefId, MonoDefId]
EdgeWithModifierContext = tuple[CallGraphEdge, ModifierContext]


@dataclass(frozen=True)
class ConcreteCustomUse:
    """A concrete custom modifier definition required by the program."""

    unmodified_callee: MonoDefId
    custom_def: MonoDefId
    kind: CustomModifierKind
    control_count: int | None


@dataclass(frozen=True)
class ModifierCallState:
    """A function invocation with modifiers inherited from its caller."""

    function: MonoDefId
    inherited_context: ModifierContext


@dataclass(frozen=True)
class ResolvedCustomCall:
    """A contextual call edge resolved to a concrete custom implementation."""

    caller: ModifierCallState
    callee: ModifierCallState
    custom_use: ConcreteCustomUse
    call: AstNode


@dataclass(frozen=True)
class ModifierCallGraphAnalysis:
    """Result of propagating modifiers through a monomorphized call graph."""

    expanded_calls: dict[MonoDefId, list[MonoDefId]]
    resolved_calls: dict[EdgeWithModifierContext, MonoDefId]
    custom_uses_by_mono_def: dict[MonoDefId, ConcreteCustomUse]


ResolveModifiedCall = Callable[
    [MonoDefId, ModifierContext], tuple[MonoDefId, ConcreteCustomUse | None]
]


def analyze_modifier_calls(
    entry_points: Iterable[MonoDefId],
    raw_calls: Mapping[MonoDefId, Sequence[MonoDefId]],
    local_modifiers_by_edge: Mapping[CallGraphEdge, Mapping[ModifierContext, AstNode]],
    resolve_modified_call: ResolveModifiedCall,
) -> ModifierCallGraphAnalysis:
    """Propagate local modifier labels and resolve concrete custom calls.

    For ``main --control(1)--> wrapper --empty--> gate``, visit ``wrapper`` with
    one inherited control and resolve its call to ``gate.controlled[1]``.
    """
    # This starts as a copy of the checked graph. Each reachable concrete caller is
    # replaced by the union of the targets found for all contexts in which it is used.
    # Unreachable and opaque generic definitions retain their original rows.
    expanded_calls = {caller: list(callees) for caller, callees in raw_calls.items()}
    # Functions whose output row has already been initialized.
    expanded_callers: set[MonoDefId] = set()
    # Resolved callees keyed by raw edge and effective modifier context.
    resolved_calls: dict[EdgeWithModifierContext, MonoDefId] = {}
    # Custom modifier uses keyed by their concrete custom monomorphization.
    custom_uses_by_mono_def: dict[MonoDefId, ConcreteCustomUse] = {}
    # Custom call occurrences retained for recursive-growth diagnostics.
    custom_calls: list[ResolvedCustomCall] = []
    # Reverse edges between `(function, inherited context)` analysis states.
    contextual_callers: defaultdict[ModifierCallState, set[ModifierCallState]] = (
        defaultdict(set)
    )

    # Entry points begin without an inherited modifier.
    worklist = [
        ModifierCallState(entry_point, NO_CALL_MODIFIERS)
        for entry_point in entry_points
        if is_concrete_inst(entry_point[1])
    ]
    visited: set[ModifierCallState] = set()

    while worklist:
        state = worklist.pop()
        if state in visited:
            continue
        visited.add(state)

        caller = state.function
        if caller not in expanded_callers:
            expanded_calls[caller] = []
            expanded_callers.add(caller)

        # The raw graph may contain the same callee once per call site. Modifier labels
        # are already grouped by edge and local context, so visit each raw edge once.
        for raw_callee in dict.fromkeys(raw_calls.get(caller, ())):
            edge = (caller, raw_callee)
            local_contexts = local_modifiers_by_edge.get(edge)
            if local_contexts is None:
                # `register_call` also records calls to definitions such as `panic`
                # whose effects are supplied directly in `func_effects`. They have no
                # checked body and therefore no local modifier label. Just preserve
                # their edge: there is no body to analyze.
                calls = ((NO_CALL_MODIFIERS, None),)
            else:
                calls = tuple(local_contexts.items())

            for local_context, call_node in calls:
                # Combine modifiers inherited from the caller with those surrounding
                # this particular call in the checked function body.
                effective_context = state.inherited_context.compose(local_context)
                resolved_callee, custom_use = resolve_modified_call(
                    raw_callee, effective_context
                )
                key = (edge, effective_context)
                previous_resolution = resolved_calls.setdefault(key, resolved_callee)
                # Different paths may reach the same edge with the same modifier
                # context. The resolved callee must be the same.
                assert previous_resolution == resolved_callee
                expanded_calls[caller].append(resolved_callee)

                if custom_use is None:
                    # No custom implementation consumed the modifiers. The compiler
                    # generates the modified callee, so its body inherits the context.
                    next_state = ModifierCallState(raw_callee, effective_context)
                    contextual_callers[next_state].add(state)
                    if raw_callee in raw_calls:
                        worklist.append(next_state)
                    continue

                # A custom implementation consumes the effective modifier context. Its
                # body is consequently analyzed with an empty inherited context.
                assert call_node is not None
                assert resolved_callee == custom_use.custom_def
                next_state = ModifierCallState(resolved_callee, NO_CALL_MODIFIERS)
                contextual_callers[next_state].add(state)
                custom_calls.append(
                    ResolvedCustomCall(state, next_state, custom_use, call_node)
                )
                existing_use = custom_uses_by_mono_def.setdefault(
                    custom_use.custom_def, custom_use
                )
                assert existing_use == custom_use
                if resolved_callee in raw_calls:
                    worklist.append(next_state)

    for caller, callees in expanded_calls.items():
        if caller in expanded_callers:
            # Multiple contextual invocations and call sites may resolve to the same
            # target. Preserve discovery order while removing duplicate graph edges.
            expanded_calls[caller] = list(dict.fromkeys(callees))

    _check_recursive_custom_uses(
        custom_calls, custom_uses_by_mono_def, contextual_callers
    )
    return ModifierCallGraphAnalysis(
        expanded_calls,
        resolved_calls,
        custom_uses_by_mono_def,
    )


def _check_recursive_custom_uses(
    custom_calls: Sequence[ResolvedCustomCall],
    custom_uses_by_mono_def: Mapping[MonoDefId, ConcreteCustomUse],
    callers: Mapping[ModifierCallState, set[ModifierCallState]],
) -> None:
    """Reject concrete recursive custom uses whose control count increases."""
    for custom_call in custom_calls:
        custom_use = custom_call.custom_use
        if custom_use.control_count is None:
            continue

        previous_count: int | None = None
        for ancestor in _call_ancestors(custom_call.caller, callers):
            ancestor_use = custom_uses_by_mono_def.get(ancestor.function)
            if (
                ancestor_use is None
                or ancestor_use.unmodified_callee != custom_use.unmodified_callee
                or ancestor_use.kind != custom_use.kind
                or ancestor_use.control_count is None
                or custom_use.control_count <= ancestor_use.control_count
            ):
                continue
            previous_count = max(previous_count or 0, ancestor_use.control_count)

        if previous_count is not None:
            raise GuppyError(
                RecursiveModifierControlCountError(
                    custom_call.call,
                    previous_count,
                    custom_use.control_count,
                )
            )


def _call_ancestors[T](callee: T, callers: Mapping[T, set[T]]) -> set[T]:
    """Return all contextual states that transitively reach ``callee``."""
    ancestors: set[T] = set()
    worklist = [callee]
    while worklist:
        current = worklist.pop()
        if current in ancestors:
            continue
        ancestors.add(current)
        worklist.extend(callers.get(current, ()))
    return ancestors
