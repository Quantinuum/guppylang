import functools
from collections.abc import Sequence
from typing import cast

from hugr import Wire, ops
from hugr import tys as ht
from hugr.build import cfg as hc
from hugr.build.dfg import DP, DfBase
from hugr.hugr.node_port import ToNode

from guppylang_internals.checker.cfg_checker import (
    CheckedBB,
    CheckedCFG,
    Row,
    Signature,
)
from guppylang_internals.checker.core import Place, Variable
from guppylang_internals.compiler.core import (
    CompilerContext,
    DFContainer,
    is_return_var,
    return_var,
)
from guppylang_internals.compiler.expr_compiler import ExprCompiler
from guppylang_internals.compiler.stmt_compiler import StmtCompiler
from guppylang_internals.std._internal.compiler.tket_bool import OpaqueBool, read_bool
from guppylang_internals.tys.ty import type_to_row


def compile_cfg(
    cfg: CheckedCFG[Place],
    container: DfBase[DP],
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

    builder = container.add_cfg(*inputs)

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

    blocks: dict[CheckedBB[Place], ToNode] = {}
    for bb in cfg.bbs:
        blocks[bb] = compile_bb(bb, builder, bb == cfg.entry_bb, ctx)
    for bb in cfg.bbs:
        for i, succ in enumerate(bb.successors):
            builder.branch(blocks[bb][i], blocks[succ])

    return builder


def compile_bb(
    bb: CheckedBB[Place],
    builder: hc.Cfg,
    is_entry: bool,
    ctx: CompilerContext,
) -> ToNode:
    """Compiles a single basic block to Hugr.

    If the basic block is the output block, returns `None`.
    """
    # The exit BB is completely empty
    if bb.is_exit:
        assert len(bb.statements) == 0
        return builder.exit

    # Unreachable BBs (besides the exit) should have been removed by now
    assert bb.reachable

    # Otherwise, we use a regular `Block` node
    block: hc.Block
    inputs: Sequence[Place]
    if is_entry:
        inputs = bb.sig.input_row
        block = builder.add_entry()
    else:
        inputs = sort_vars(bb.sig.input_row)
        block = builder.add_block(*(v.ty.to_hugr(ctx) for v in inputs))

    # Add input node and compile the statements
    dfg = DFContainer(block, ctx)
    for v, wire in zip(inputs, block.input_node, strict=True):
        dfg[v] = wire
    dfg = StmtCompiler(ctx).compile_stmts(bb.statements, dfg)

    # If we branch, we also have to compile the branch predicate
    if len(bb.successors) > 1:
        assert bb.branch_pred is not None
        branch_port = ExprCompiler(ctx).compile(bb.branch_pred, dfg)
        # Convert the bool predicate into a sum for branching.
        pred_ty = builder.hugr.port_type(branch_port.out_port())
        assert pred_ty == OpaqueBool
        branch_port = dfg.builder.add_op(read_bool(), branch_port)
        branch_port = cast("Wire", branch_port)
    else:
        # Even if we don't branch, we still have to add a `Sum(())` predicates
        branch_port = dfg.builder.add_op(ops.Tag(0, ht.UnitSum(1)))

    # Finally, we have to add the block output.
    outputs: Sequence[Place]
    if len(bb.successors) == 1:
        # The easy case is if we don't branch: We just output all variables that are
        # specified by the signature
        [outputs] = bb.sig.output_rows
    else:
        # CFG building ensures that branching BBs don't branch to the exit (exit jumps
        # must always be unconditional)
        assert not any(succ.is_exit for succ in bb.successors)

        # If we branch and the branches use the same places, then we can use a
        # regular output
        first, *rest = bb.sig.output_rows
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
                    [v for v in sort_vars(row) if v.ty.droppable]
                    for row in bb.sig.output_rows
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

    # We pass all values into the conditional instead of relying on non-local edges.
    # This is because we can't handle them in lower parts of the stack yet :/
    # TODO: Reinstate use of non-local edges.
    #  See https://github.com/quantinuum/guppylang/issues/963
    all_vars = {v.id: dfg[v] for var_row in output_vars for v in var_row}
    all_vars_wires = list(all_vars.values())
    all_vars_idxs = {x: i for i, x in enumerate(all_vars.keys())}

    with dfg.builder.add_conditional(unit_sum, *all_vars_wires) as conditional:
        for i, var_row in enumerate(output_vars):
            with conditional.add_case(i) as case:
                case_inputs = case.inputs()
                outputs = [case_inputs[all_vars_idxs[v.id]] for v in var_row]
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
