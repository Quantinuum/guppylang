from collections import deque
from collections.abc import Iterator
from typing import Generic, TypeVar

from guppylang_internals.cfg.analysis import (
    AssignmentAnalysis,
    DefAssignmentDomain,
    LivenessAnalysis,
    LivenessDomain,
    MaybeAssignmentDomain,
    Result,
)
from guppylang_internals.cfg.bb import BB, BBStatement, VariableStats
from guppylang_internals.nodes import InoutReturnSentinel
from guppylang_internals.tys.ty import UnitaryFlags

T = TypeVar("T", bound=BB)


class BaseCFG(Generic[T]):
    """Abstract base class for control-flow graphs."""

    bbs: list[T]
    entry_bb: T
    exit_bb: T

    live_before: Result[LivenessDomain[str]]
    ass_before: Result[DefAssignmentDomain[str]]
    maybe_ass_before: Result[MaybeAssignmentDomain[str]]

    #: Set of variables defined in this CFG
    assigned_somewhere: set[str]
    unitary_flags: UnitaryFlags

    def __init__(
        self, bbs: list[T], entry_bb: T | None = None, exit_bb: T | None = None
    ):
        self.bbs = bbs
        if entry_bb:
            self.entry_bb = entry_bb
        if exit_bb:
            self.exit_bb = exit_bb
        self.live_before = {}
        self.ass_before = {}
        self.maybe_ass_before = {}
        self.assigned_somewhere = set()
        self.unitary_flags = UnitaryFlags.NoFlags

    def ancestors(self, *bbs: T) -> Iterator[T]:
        """Returns an iterator over all ancestors of the given BBs in BFS order."""
        queue = deque(bbs)
        visited = set()
        while queue:
            bb = queue.popleft()
            if bb in visited:
                continue
            visited.add(bb)
            yield bb
            queue += bb.predecessors

    def update_reachable(self) -> None:
        """Sets the reachability flags on the BBs in this CFG."""
        queue = {self.entry_bb}
        while queue:
            bb = queue.pop()
            if not bb.reachable:
                bb.reachable = True
                for succ in bb.successors:
                    queue.add(succ)


class CFG(BaseCFG[BB]):
    """A control-flow graph of unchecked basic blocks."""

    def __init__(self) -> None:
        super().__init__([])
        self.entry_bb = self.new_bb()
        self.exit_bb = self.new_bb()

    def new_bb(self, *preds: BB, statements: list[BBStatement] | None = None) -> BB:
        """Adds a new basic block to the CFG."""
        bb = BB(
            len(self.bbs), self, predecessors=list(preds), statements=statements or []
        )
        self.bbs.append(bb)
        for p in preds:
            p.successors.append(bb)
        return bb

    def link(self, src_bb: BB, tgt_bb: BB) -> None:
        """Adds a control-flow edge between two basic blocks."""
        src_bb.successors.append(tgt_bb)
        tgt_bb.predecessors.append(src_bb)

    def dummy_link(self, src_bb: BB, tgt_bb: BB) -> None:
        """Adds a dummy control-flow edge between two basic blocks that is provably
        never taken.

        For example, a `if False: ...` statement emits such a dummy link.
        """
        src_bb.dummy_successors.append(tgt_bb)
        tgt_bb.dummy_predecessors.append(src_bb)

    def analyze(
        self,
        def_ass_before: set[str],
        maybe_ass_before: set[str],
        inout_vars: list[str],
    ) -> dict[BB, VariableStats[str]]:
        stats = {bb: bb.compute_variable_stats() for bb in self.bbs}
        # Locals are variables that are assigned somewhere inside the function
        self.assigned_somewhere = def_ass_before.union(
            maybe_ass_before, (x for bb in self.bbs for x in stats[bb].assigned)
        )
        # Mark all borrowed variables as implicitly used in the exit BB
        stats[self.exit_bb].used |= {x: InoutReturnSentinel(var=x) for x in inout_vars}
        # This also means borrowed variables are always live, so we can use them as the
        # initial value in the liveness analysis. This solves the edge case that
        # borrowed variables should be considered live, even if the exit is actually
        # unreachable (to avoid linearity violations later).
        inout_live = dict.fromkeys(inout_vars, self.exit_bb)
        self.live_before = LivenessAnalysis(
            stats, initial=inout_live, include_unreachable=True
        ).run(self.bbs)
        self.ass_before, self.maybe_ass_before = AssignmentAnalysis(
            stats, def_ass_before, maybe_ass_before, include_unreachable=True
        ).run_unpacked(self.bbs)
        return stats
