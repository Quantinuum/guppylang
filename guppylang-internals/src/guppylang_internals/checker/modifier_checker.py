"""Type checking code for modifiers."""

import ast

from guppylang_internals.ast_util import loop_in_ast, with_loc
from guppylang_internals.cfg.bb import BB
from guppylang_internals.checker.cfg_checker import check_cfg
from guppylang_internals.checker.core import Context, Variable
from guppylang_internals.checker.errors.generic import InvalidUnderDagger
from guppylang_internals.definition.common import DefId
from guppylang_internals.error import GuppyError
from guppylang_internals.nodes import CheckedModifiedBlock, ModifiedBlock
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    Type,
)


def check_modified_block(
    modified_block: ModifiedBlock, bb: BB, ctx: Context
) -> CheckedModifiedBlock:
    """Type checks a modifier definition."""
    cfg = modified_block.cfg

    # Find captured variables
    parent_cfg = bb.containing_cfg
    def_ass_before = ctx.locals.keys()
    maybe_ass_before = def_ass_before | parent_cfg.maybe_ass_before[bb]

    cfg.analyze(def_ass_before, maybe_ass_before, [])
    captured = {
        x: (_set_inout_if_non_copyable(ctx.locals[x]), using_bb.vars.used[x])
        for x, using_bb in cfg.live_before[cfg.entry_bb].items()
        if x in ctx.locals
    }

    # We do not allow any assignments if it is daggered.
    if modified_block.is_dagger():
        for stmt in modified_block.body:
            loops = loop_in_ast(stmt)
            if len(loops) != 0:
                loop = next(iter(loops))
                err = InvalidUnderDagger(loop, "Loop")
                err.add_sub_diagnostic(
                    InvalidUnderDagger.Dagger(modified_block.span_ctxt_manager())
                )
                raise GuppyError(err)

        for cfg_bb in cfg.bbs:
            if cfg_bb.vars.assigned:
                _, v = next(iter(cfg_bb.vars.assigned.items()))
                err = InvalidUnderDagger(v, "Assignment")
                err.add_sub_diagnostic(
                    InvalidUnderDagger.Dagger(modified_block.span_ctxt_manager())
                )
                raise GuppyError(err)

    # The other checks are done in unitary checking.
    # e.g. call to non-unitary function in a unitary modifier.

    # Construct inputs for checking the body CFG
    inputs = [v for v, _ in captured.values()]
    inputs = non_copyable_front_others_back(inputs)
    def_id = DefId.fresh()
    globals = ctx.globals

    # TODO: Ad hoc name for the new function
    # This name could be printed in error messages, for example,
    # when the linearity checker fails in the modifier body
    checked_cfg = check_cfg(cfg, inputs, NoneType(), {}, "__modified__()", globals)
    func_ty = check_modified_block_signature(modified_block, checked_cfg.input_tys)

    checked_modifier = CheckedModifiedBlock(
        def_id,
        checked_cfg,
        func_ty,
        captured,
        modified_block.dagger,
        modified_block.control,
        modified_block.power,
        **dict(ast.iter_fields(modified_block)),
    )
    return with_loc(modified_block, checked_modifier)


def _set_inout_if_non_copyable(var: Variable) -> Variable:
    """Set the `inout` flag if the variable is non-copyable."""
    if not var.ty.copyable:
        return var.add_flags(InputFlags.Inout)
    else:
        return var


def check_modified_block_signature(
    modified_block: ModifiedBlock, input_tys: list[Type]
) -> FunctionType:
    """Check and create the signature of a function definition for a body
    of a `With` block."""
    unitary_flags = modified_block.flags()

    func_ty = FunctionType(
        [
            FuncInput(t, InputFlags.Inout if not t.copyable else InputFlags.NoFlags)
            for t in input_tys
        ],
        NoneType(),
        unitary_flags=unitary_flags,
    )
    return func_ty


def non_copyable_front_others_back(v: list[Variable]) -> list[Variable]:
    """Reorder variables so that linear ones come first, preserving the relative order
    of linear and non-linear variables."""
    linear_vars = [x for x in v if not x.ty.copyable]
    non_linear_vars = [x for x in v if x.ty.copyable]
    return linear_vars + non_linear_vars
