import functools
from collections.abc import Mapping, Sequence

from hugr import Wire
from hugr import tys as ht
from hugr.build import cfg as hc
from hugr.hugr.node_port import ToNode

from guppylang_internals.checker.cfg_checker import (
    CheckedBB,
    CheckedCFG,
    Row,
    Signature,
)
from guppylang_internals.checker.core import Place, PlaceId, Variable
from guppylang_internals.compiler.builder import BlockBuilder, DFBuilder, ops
from guppylang_internals.compiler.core import (
    CompilerContext,
    DFContainer,
    is_return_var,
    return_var,
)
from guppylang_internals.compiler.expr_compiler import ExprCompiler
from guppylang_internals.compiler.stmt_compiler import StmtCompiler
from guppylang_internals.tys.ty import type_to_row


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

    blocks: dict[CheckedBB[Place], tuple[ToNode, Sequence[hc.Block | None]]] = {}
    for bb in cfg.bbs:
        blocks[bb] = compile_bb(bb, builder, container, bb == cfg.entry_bb, ctx)
    for bb in cfg.bbs:
        block, adaptors = blocks[bb]
        for i, (succ, adaptor) in enumerate(zip(bb.successors, adaptors, strict=True)):
            (tgt, _) = blocks[succ]
            if adaptor is None:
                builder.branch(block[i], tgt)
            else:
                builder.branch(block[i], adaptor)
                builder.branch(adaptor, tgt)

    return builder


def compile_bb(
    bb: CheckedBB[Place],
    builder: hc.Cfg,
    outer: DFBuilder,
    is_entry: bool,
    ctx: CompilerContext,
) -> tuple[ToNode, Sequence[hc.Block | None]]:
    """Compiles a single basic block to Hugr. Returns the block,
    and for each successor an optional extra block which must intervene
    on the edge to that successor.
    """
    # The exit BB is completely empty
    if bb.is_exit:
        assert len(bb.statements) == 0
        return builder.exit, []

    # Unreachable BBs (besides the exit) should have been removed by now
    assert bb.reachable

    # Otherwise, we use a regular `Block` node
    hugr_block: hc.Block
    inputs: Sequence[Place]
    if is_entry:
        inputs = bb.sig.input_row
        hugr_block = builder.add_entry()
    else:
        inputs = sort_vars(bb.sig.input_row)
        hugr_block = builder.add_block(*(v.ty.to_hugr(ctx) for v in inputs))
    block = BlockBuilder(hugr_block, builder, outer)
    # Add input node and compile the statements
    dfg = DFContainer(block, ctx)
    for v, wire in zip(inputs, block.input_node, strict=True):
        dfg[v] = wire
    dfg = StmtCompiler(ctx).compile_stmts(bb.statements, dfg)

    # If we branch, we also have to compile the branch predicate
    if len(bb.successors) > 1:
        assert bb.branch_pred is not None
        branch_port = ExprCompiler(ctx).compile(bb.branch_pred, dfg)
    else:
        # Even if we don't branch, we still have to add a `Sum(())` predicates
        branch_port = dfg.builder.add_op(
            ops.tag(0, ht.UnitSum(1)), set_debug_info=False
        )

    # Finally, we have to add the block output, generating adaptor blocks
    # to filter outputs down to those required by each successor if necessary.
    outputs: Sequence[Place]
    succ_adaptors: list[hc.Block | None] = [None for _ in bb.successors]
    if len(bb.successors) == 1:
        # The easy case is if we don't branch: We just output all variables that are
        # specified by the signature
        [outputs] = bb.sig.output_rows
        if not bb.successors[0].is_exit:
            outputs = sort_vars(outputs)  # Keep consistent with successor
    else:
        # CFG building ensures that branching BBs don't branch to the exit (exit jumps
        # must always be unconditional)
        assert not any(succ.is_exit for succ in bb.successors)

        # Identify all variables used by any successor block
        var_map: Mapping[PlaceId, Place] = {
            p.id: p for row in bb.sig.output_rows for p in row
        }
        outputs = sort_vars(list(var_map.values()))
        # Can we use 'Dom` edges for droppable outputs? I think no - each output is
        # used by some BB as an actual input, so we must pass them as explicit outputs.
        for i, r in enumerate(bb.sig.output_rows):
            if len(r) == len(var_map):
                assert {p.id for p in r} == {p.id for p in var_map.values()}
                # Can jump directly
            else:
                # Add a basic block that discards the unused ones
                tgt_block = builder.add_block(*(v.ty.to_hugr(ctx) for v in outputs))
                tgt_builder = BlockBuilder(tgt_block, builder, outer)
                input_map = {
                    v.id: p for v, p in zip(outputs, tgt_block.input_node, strict=True)
                }
                branch_val = tgt_builder.add_op(
                    ops.tag(0, ht.UnitSum(1)), set_debug_info=False
                )
                tgt_builder.set_block_outputs(
                    branch_val, *(input_map[p.id] for p in sort_vars(r))
                )
                succ_adaptors[i] = tgt_block

    block.set_block_outputs(branch_port, *(dfg[v] for v in outputs))
    return block, succ_adaptors


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
