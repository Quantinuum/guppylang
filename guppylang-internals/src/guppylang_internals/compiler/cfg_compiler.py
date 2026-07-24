import ast
import functools
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field

from hugr import Wire, ops
from hugr import tys as ht
from hugr.build import cfg as hc
from hugr.hugr.node_port import ToNode

from guppylang_internals.cfg.analysis import (
    compute_dominators,
    loop_blocks,
    reverse_postorder,
)
from guppylang_internals.checker.cfg_checker import (
    CheckedBB,
    CheckedCFG,
    Row,
    Signature,
)
from guppylang_internals.checker.core import Place, PlaceId, Variable
from guppylang_internals.compiler.builder import BlockBuilder, DFBuilder
from guppylang_internals.compiler.core import (
    CompilerContext,
    DFContainer,
    is_return_var,
    return_var,
)
from guppylang_internals.compiler.expr_compiler import ExprCompiler
from guppylang_internals.compiler.stmt_compiler import StmtCompiler
from guppylang_internals.nodes import (
    ArrayUnpack,
    IterableUnpack,
    ModifiedBlock,
    PlaceNode,
    TupleUnpack,
    UnpackPattern,
)
from guppylang_internals.std._internal.compiler.tket_exts import MEASUREMENT_EXTENSION
from guppylang_internals.tys.ty import StructType, TupleType, type_to_row

_MEASUREMENT_HUGR_TYPE: ht.Type = ht.ExtType(
    MEASUREMENT_EXTENSION.get_type("Measurement")
)


def _is_dethreadable_place(place: Place, ctx: CompilerContext) -> bool:
    """Whether a place is a candidate for non-local (Dom-edge) de-threading.

    We bypass block signatures for *copyable scalar* variables: copyable so the
    value can be duplicated across a non-local edge, and scalar (not a struct or
    tuple) so that its wire is stored directly and delivering it never inserts
    extra pack/unpack ops. Linear values must stay threaded (they can't be
    duplicated), and return variables are handled separately by the exit block.

    Copyability is checked at the *Hugr* level too, not just guppy's
    `Type.copyable`, so a value that lowers to a linear Hugr type is never
    de-threaded.

    `Measurement` is the known edge case we explicitly exclude (see the comment
    on the check below): it is copyable in the surface language but the Helios QIS
    lowering treats it as linear on a non-local edge.
    """
    if not (
        isinstance(place, Variable)
        and not is_return_var(place.name)
        and place.ty.copyable
        and not isinstance(place.ty, StructType | TupleType)
    ):
        return False
    hugr_ty = place.ty.to_hugr(ctx)
    # `Measurement` is really a *future* that guppy auto-copies at the surface
    # level (so `Type.copyable` and the Hugr type bound both report copyable), yet
    # the Helios QIS lowering still treats it as linear and rejects it on a
    # non-local edge ("Cannot add nonlocal edge for linear type"). Exclude it as a
    # narrow, type-specific carve-out rather than a general type restriction.
    # TODO: Drop this carve-out once Quantinuum/tket2#1883 (type-scoped
    # LocalizeEdges for linearised non-local edges) lands.
    return (
        hugr_ty.type_bound() == ht.TypeBound.Copyable
        and hugr_ty != _MEASUREMENT_HUGR_TYPE
    )


def _target_place_ids(target: ast.expr) -> Iterator[PlaceId]:
    """Yields the place ids assigned by an assignment target expression."""
    match target:
        case PlaceNode(place=place):
            yield place.id
        case TupleUnpack(pattern=pattern) | ArrayUnpack(pattern=pattern):
            yield from _pattern_place_ids(pattern)
        case IterableUnpack(pattern=pattern):
            yield from _pattern_place_ids(pattern)
        case ast.Tuple(elts=elts) | ast.List(elts=elts):
            for elt in elts:
                yield from _target_place_ids(elt)
        case ast.Starred(value=value):
            yield from _target_place_ids(value)
        case _:
            return


def _pattern_place_ids(pattern: UnpackPattern) -> Iterator[PlaceId]:
    for elt in pattern.left:
        yield from _target_place_ids(elt)
    if pattern.starred is not None:
        yield from _target_place_ids(pattern.starred)
    for elt in pattern.right:
        yield from _target_place_ids(elt)


def _assigned_place_ids(bb: CheckedBB[Place]) -> set[PlaceId]:
    """The place ids that are (re)assigned by the statements of a basic block.

    This walks assignment targets directly, since the checked statements use
    `PlaceNode` targets that the name-based `VariableStats` visitor doesn't see.
    Crucially it catches loop-carried reassignments (a place that a block both
    reads and writes), which the block signature alone cannot distinguish from a
    pass-through. Over-approximating here is safe: an extra apparent definition
    only makes us keep threading a place.
    """
    assigned: set[PlaceId] = set()

    def visit(stmt: ast.stmt) -> None:
        match stmt:
            case ast.Assign(targets=targets):
                for target in targets:
                    assigned.update(_target_place_ids(target))
            case ast.AnnAssign(target=target) | ast.AugAssign(target=target):
                assigned.update(_target_place_ids(target))
            case ModifiedBlock(body=body):
                for inner in body:
                    visit(inner)
            case _:
                return

    for stmt in bb.statements:
        visit(stmt)
    return assigned


@dataclass(frozen=True)
class DethreadInfo:
    """Result of the de-threading analysis for a CFG.

    Records which places should be delivered via non-local Dom edges instead of
    being threaded through block signatures, together with the (unique) block
    that defines each such place.
    """

    #: The `PlaceId`s that should bypass block signatures.
    ids: frozenset[PlaceId] = field(default_factory=frozenset)
    #: The unique defining block for each de-threaded place.
    def_block: dict[PlaceId, CheckedBB[Place]] = field(default_factory=dict)
    #: A representative `Place` object for each de-threaded id.
    place: dict[PlaceId, Place] = field(default_factory=dict)

    def defined_in(self, bb: CheckedBB[Place]) -> list[Place]:
        """The de-threaded places whose definition lives in `bb`."""
        return [self.place[i] for i, d in self.def_block.items() if d is bb]


def compute_dethread_info(cfg: CheckedCFG[Place], ctx: CompilerContext) -> DethreadInfo:
    """Determines which copyable places can be de-threaded via Dom edges.

    A place is de-threaded when it is a copyable scalar variable with a *single*
    definition whose block *strictly dominates* every block in which the place is
    live. In guppy's reducible CFGs this is exactly the "live but unused in this
    block" pass-through case (e.g. the booleans of a short-circuiting `or` chain)
    that otherwise blows up block signatures to O(W^2).
    """
    dominators = compute_dominators(cfg.entry_bb)
    # Blocks inside a loop may execute multiple times. Delivering a value into
    # such a block via a single non-local edge from a dominating definition is
    # semantically fine for copyable values, but some backends (e.g. the Helios
    # QIS lowering) cannot lower a non-local edge whose target executes more than
    # once for resource-like copyable types. Staying conservative here also keeps
    # us clearly correct, so we never de-thread a value used inside a loop.
    in_loop = loop_blocks(cfg.entry_bb)

    # Collect, per place id: the blocks where it is live-in, the blocks that
    # define it, and a representative place object.
    live_in: dict[PlaceId, set[CheckedBB[Place]]] = {}
    defs: dict[PlaceId, set[CheckedBB[Place]]] = {}
    place_obj: dict[PlaceId, Place] = {}
    eligible: set[PlaceId] = set()

    def note(place: Place) -> None:
        if place.id not in place_obj:
            place_obj[place.id] = place
            if _is_dethreadable_place(place, ctx):
                eligible.add(place.id)

    for bb in cfg.bbs:
        if bb not in dominators:
            # Unreachable block that wasn't visited from the entry: ignore it.
            continue
        in_ids = {p.id for p in bb.sig.input_row}
        for place in bb.sig.input_row:
            note(place)
            live_in.setdefault(place.id, set()).add(bb)
        # The entry block defines its inputs (the function arguments).
        if bb is cfg.entry_bb:
            for place in bb.sig.input_row:
                defs.setdefault(place.id, set()).add(bb)
        # A block defines every place that is live on the way out but wasn't live
        # on the way in...
        for row in bb.sig.output_rows:
            for place in row:
                note(place)
                if place.id not in in_ids:
                    defs.setdefault(place.id, set()).add(bb)
        # ...as well as every place it (re)assigns via a statement. The latter is
        # essential for loop-carried values, which a block both reads and writes
        # (so they show up in both its input and output rows and are invisible to
        # the signature check above).
        for pid in _assigned_place_ids(bb):
            defs.setdefault(pid, set()).add(bb)

    ids: set[PlaceId] = set()
    def_block: dict[PlaceId, CheckedBB[Place]] = {}
    # Places that are live into the exit block are CFG outputs (return values).
    # The exit's expected input types are fixed independently of the block
    # signatures, so these must always be delivered by normal threading.
    exit_ids = {p.id for p in cfg.exit_bb.sig.input_row}
    for pid in eligible - exit_ids:
        def_blocks = defs.get(pid, set())
        if len(def_blocks) != 1:
            # No definition, or multiple (e.g. phi-merge on divergent branches):
            # keep threading to stay correct.
            continue
        (definition,) = def_blocks
        # The definition must strictly dominate every block where the place is
        # live (so a Dom edge from the definition is always valid), and no use may
        # sit inside a loop (see `in_loop` above).
        uses = live_in.get(pid, set())
        if any(use in in_loop for use in uses):
            continue
        if all(
            use is definition or definition in dominators.get(use, frozenset())
            for use in uses
        ):
            ids.add(pid)
            def_block[pid] = definition

    return DethreadInfo(
        ids=frozenset(ids),
        def_block=def_block,
        place={pid: place_obj[pid] for pid in ids},
    )


def compile_cfg(
    cfg: CheckedCFG[Place],
    container: DFBuilder,
    inputs: Sequence[Wire],
    ctx: CompilerContext,
) -> hc.Cfg:
    """Compiles a CFG to Hugr."""
    # Patch the CFG with dummy return variables
    # TODO: This mutates the CFG in-place which leads to problems when trying to lower
    #  the same function to Hugr twice. For now we just check that the return vars
    #  haven't already been inserted, but we should figure out a better way to handle
    #  this: https://github.com/quantinuum/guppylang/issues/428
    if all(
        not is_return_var(v.name)
        for v in cfg.exit_bb.sig.input_row
        if isinstance(v, Variable)
    ):
        insert_return_vars(cfg)

    builder: hc.Cfg = container.add_cfg(*inputs)

    # Explicitly annotate the output types since Hugr can't infer them if the exit is
    # unreachable
    out_tys = [place.ty.to_hugr(ctx) for place in cfg.exit_bb.sig.input_row]
    # TODO: Use proper API for this once it's added in hugr-py:
    #  https://github.com/quantinuum/hugr/issues/1816
    builder._exit_op._cfg_outputs = out_tys
    builder.parent_op._outputs = out_tys
    builder.parent_node = builder.hugr._update_node_outs(
        builder.parent_node, len(out_tys)
    )

    # Figure out which copyable values can bypass block signatures via Dom edges.
    dethread = compute_dethread_info(cfg, ctx)
    # Wires of de-threaded places, keyed by place id, populated as their defining
    # block is compiled. Blocks are compiled in reverse postorder so that a
    # definition is always compiled before the (dominated) blocks that use it.
    dethreaded_wires: dict[PlaceId, Wire] = {}

    ordered_bbs = reverse_postorder(cfg.entry_bb)
    seen = set(ordered_bbs)
    ordered_bbs += [bb for bb in cfg.bbs if bb not in seen]

    blocks: dict[CheckedBB[Place], ToNode] = {}
    for bb in ordered_bbs:
        blocks[bb] = compile_bb(
            bb,
            builder,
            container,
            bb == cfg.entry_bb,
            ctx,
            dethread,
            dethreaded_wires,
        )
    for bb in cfg.bbs:
        for i, succ in enumerate(bb.successors):
            builder.branch(blocks[bb][i], blocks[succ])

    return builder


def compile_bb(
    bb: CheckedBB[Place],
    builder: hc.Cfg,
    outer: DFBuilder,
    is_entry: bool,
    ctx: CompilerContext,
    dethread: DethreadInfo | None = None,
    dethreaded_wires: dict[PlaceId, Wire] | None = None,
) -> ToNode:
    """Compiles a single basic block to Hugr.

    If the basic block is the output block, returns `None`.
    """
    if dethread is None:
        dethread = DethreadInfo()
    if dethreaded_wires is None:
        dethreaded_wires = {}

    # The exit BB is completely empty
    if bb.is_exit:
        assert len(bb.statements) == 0
        return builder.exit

    # Unreachable BBs (besides the exit) should have been removed by now
    assert bb.reachable

    def keep(place: Place) -> bool:
        return place.id not in dethread.ids

    # De-threaded places bypass the block signature. The entry block keeps its
    # full input row since that is the function signature; other blocks drop the
    # de-threaded places, which are instead pulled in via Dom edges.
    output_rows = [[p for p in row if keep(p)] for row in bb.sig.output_rows]

    # Otherwise, we use a regular `Block` node
    hugr_block: hc.Block
    inputs: Sequence[Place]
    if is_entry:
        inputs = bb.sig.input_row
        hugr_block = builder.add_entry()
    else:
        inputs = sort_vars([p for p in bb.sig.input_row if keep(p)])
        hugr_block = builder.add_block(*(v.ty.to_hugr(ctx) for v in inputs))
    block = BlockBuilder(hugr_block, builder, outer)
    # Add input node and compile the statements
    dfg = DFContainer(block, ctx)
    for v, wire in zip(inputs, block.input_node, strict=True):
        dfg[v] = wire
    # Supply de-threaded places that are live here but defined in a dominating
    # block by referencing that block's wire. hugr-py turns this into a non-local
    # Dom edge when the value is actually used.
    for place in bb.sig.input_row:
        if place.id in dethread.ids and dethread.def_block.get(place.id) is not bb:
            dfg[place] = dethreaded_wires[place.id]
    dfg = StmtCompiler(ctx).compile_stmts(bb.statements, dfg)

    # Record wires for de-threaded places defined in this block so that dominated
    # blocks can pull them in.
    for place in dethread.defined_in(bb):
        dethreaded_wires[place.id] = dfg[place]

    # If we branch, we also have to compile the branch predicate
    if len(bb.successors) > 1:
        assert bb.branch_pred is not None
        branch_port = ExprCompiler(ctx).compile(bb.branch_pred, dfg)
    else:
        # Even if we don't branch, we still have to add a `Sum(())` predicates
        branch_port = dfg.builder.add_op(
            ops.Tag(0, ht.UnitSum(1)), set_debug_info=False
        )

    # Finally, we have to add the block output.
    outputs: Sequence[Place]
    if len(bb.successors) == 1:
        # The easy case is if we don't branch: We just output all variables that are
        # specified by the signature
        [outputs] = output_rows
    else:
        # CFG building ensures that branching BBs don't branch to the exit (exit jumps
        # must always be unconditional)
        assert not any(succ.is_exit for succ in bb.successors)

        # If we branch and the branches use the same places, then we can use a
        # regular output
        first, *rest = output_rows
        if all({p.id for p in first} == {p.id for p in r} for r in rest):
            outputs = first
        else:
            # Otherwise, we have to output a TupleSum: We put all non-linear variables
            # into the branch TupleSum and all linear variables in the normal output
            # (since they are shared between all successors). This is in line with the
            # ordering on variables which puts linear variables at the end.
            # We don't need to worry about the order of return vars since this isn't
            # a branch to an exit (see assert above).
            branch_port = choose_vars_for_tuple_sum(
                unit_sum=branch_port,
                output_vars=[
                    [v for v in sort_vars(row) if v.ty.droppable] for row in output_rows
                ],
                dfg=dfg,
            )
            outputs = [v for v in first if not v.ty.droppable]

    # If this is *not* a jump to the exit BB, we need to sort the outputs to make the
    # signature consistent with what the next BB expects
    if not any(succ.is_exit for succ in bb.successors):
        outputs = sort_vars(outputs)
    else:
        # Exit variables are not allowed to be sorted since their order corresponds to
        # the function outputs
        assert len(bb.successors) == 1, "Exit jumps are always unconditional"

    block.set_block_outputs(branch_port, *(dfg[v] for v in outputs))
    return block


def insert_return_vars(cfg: CheckedCFG[Place]) -> None:
    """Patches a CFG by annotating dummy return variables in the BB signatures.

    The statement compiler turns `return` statements into assignments of dummy variables
    `%ret0`, `%ret1`, etc. We update the exit BB signature to make sure they are
    correctly outputted.
    """
    return_vars = [
        Variable(return_var(i), ty, None)
        for i, ty in enumerate(type_to_row(cfg.output_ty))
    ]
    # Prepend return variables to the exit signature
    cfg.exit_bb.sig = Signature(
        [*return_vars, *cfg.exit_bb.sig.input_row], cfg.exit_bb.sig.output_rows
    )
    # Also patch the predecessors
    for pred in cfg.exit_bb.predecessors:
        # The exit BB will be the only successor
        assert len(pred.sig.output_rows) == 1
        [out_row] = pred.sig.output_rows
        pred.sig = Signature(pred.sig.input_row, [[*return_vars, *out_row]])


def choose_vars_for_tuple_sum(
    unit_sum: Wire, output_vars: list[Row[Place]], dfg: DFContainer
) -> Wire:
    """Selects an output based on a TupleSum.

    Given `unit_sum: Sum(*(), *(), ...)` and output variable rows `#s1, #s2, ...`,
    constructs a TupleSum value of type `Sum(#s1, #s2, ...)`.
    """
    assert all(v.ty.droppable for var_row in output_vars for v in var_row)
    sum_type = ht.Sum(
        [[v.ty.to_hugr(dfg.ctx) for v in var_row] for var_row in output_vars]
    )

    # Non-copyable types must be passed into the conditional since we can't use
    # inter-graph (non-local) edges to feed them in implicitly. Copyable values are
    # read directly from the enclosing DFG via non-local edges instead of being
    # threaded through the conditional's input signature.
    non_copyable = {
        v.id: dfg[v] for var_row in output_vars for v in var_row if not v.ty.copyable
    }
    non_copyable_wires = list(non_copyable.values())
    non_copyable_idxs = {x: i for i, x in enumerate(non_copyable.keys())}

    with dfg.builder.add_conditional(unit_sum, *non_copyable_wires) as conditional:
        for i, var_row in enumerate(output_vars):
            case = conditional.add_case(i)
            case_inputs = case.inputs()
            outputs = [
                dfg[v] if v.ty.copyable else case_inputs[non_copyable_idxs[v.id]]
                for v in var_row
            ]
            tag = case.add_op(ops.Tag(i, sum_type), *outputs)
            case.set_outputs(tag)
        return conditional


def compare_var(p1: Place, p2: Place) -> int:
    """Defines a `<` order on variables.

    We use this to determine in which order variables are outputted from basic blocks.
    We need to output linear variables at the end, so we do a lexicographic ordering of
    linearity and name.
    """
    return -1 if (not p1.ty.droppable, str(p1)) < (not p2.ty.droppable, str(p2)) else 1


def sort_vars(row: Row[Place]) -> list[Place]:
    """Sorts a row of variables.

    This determines the order in which they are outputted from a BB.
    """
    return sorted(row, key=functools.cmp_to_key(compare_var))
