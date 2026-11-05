"""Type checking code for modifiers."""

import ast
from collections.abc import Mapping

from guppylang_internals.ast_util import set_location_from, with_loc
from guppylang_internals.cfg.bb import BB
from guppylang_internals.cfg.cfg import CFG
from guppylang_internals.checker.cfg_checker import check_cfg
from guppylang_internals.checker.core import (
    Context,
    FieldAccess,
    Place,
    PlaceId,
    TupleAccess,
    Variable,
)
from guppylang_internals.checker.linearity_checker import parent_places
from guppylang_internals.checker.unitary_checker import check_invalid_under_dagger
from guppylang_internals.engine import ENGINE
from guppylang_internals.error import InternalGuppyError
from guppylang_internals.nodes import (
    CheckedModifiedBlock,
    ComptimeExpr,
    ModifiedBlock,
    NestedFunctionDef,
)
from guppylang_internals.tys import Effect
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    StructType,
    TupleType,
    Type,
)


def check_modified_block(
    modified_block: ModifiedBlock, bb: BB, ctx: Context
) -> CheckedModifiedBlock:
    """Type checks a modifier definition."""
    cfg = modified_block.cfg

    if not ctx.current_caller:
        raise InternalGuppyError("current_caller required to check with block!")

    # Find captured variables
    parent_cfg = bb.containing_cfg
    def_ass_before = ctx.locals.keys()
    maybe_ass_before = def_ass_before | parent_cfg.maybe_ass_before[bb]

    cfg.analyze(def_ass_before, maybe_ass_before, [])

    # If the body only accesses some fields of a struct or elements of a tuple, we
    # capture those instead of the whole value. This allows, for example, using one
    # field of a struct as control while acting on another field inside the body.
    captured_projections = _capture_projections(
        cfg,
        {
            x: ctx.locals[x]
            for x in cfg.live_before[cfg.entry_bb]
            if x in ctx.locals and isinstance(ctx.locals[x].ty, StructType | TupleType)
        },
    )
    if captured_projections:
        def_ass_before = def_ass_before | captured_projections.keys()
        maybe_ass_before = maybe_ass_before | captured_projections.keys()
        cfg.analyze(def_ass_before, maybe_ass_before, [])

    captured = {
        x: (
            captured_projections[x] if x in captured_projections else ctx.locals[x],
            using_bb.vars.used[x],
        )
        for x, using_bb in cfg.live_before[cfg.entry_bb].items()
        if x in captured_projections or x in ctx.locals
    }

    # We do not allow any loop or branching if it is daggered.
    check_invalid_under_dagger(modified_block, modified_block.accumulated_flags)
    # The other checks are done in unitary checking.
    # e.g. call to non-unitary function in a unitary modifier.

    # Construct inputs for checking the body CFG
    inputs = [_body_input(x, place) for x, (place, _) in captured.items()]
    inputs = non_copyable_front_others_back(inputs)
    globals = ctx.globals
    assert ctx.modified_block_counter is not None
    block_name = (
        f"{ctx.modified_block_name_base}."
        f"__WithBlock__{next(ctx.modified_block_counter)}"
    )
    checked_cfg = check_cfg(
        cfg,
        inputs,
        NoneType(),
        ctx.generic_param_inst,
        "__modified__()",
        globals,
        current_caller=ctx.current_caller,
        modifier_ctx=ctx.modifier_ctx,
        # We pass the first modifier node for better error messages in the cfg checker
        first_modifier_node=modified_block.first_modifier_node,
        modified_block_name_base=ctx.modified_block_name_base,
        modified_block_counter=ctx.modified_block_counter,
    )
    if ctx.modifier_ctx.control_sizes:
        # Array manipulation code for controls, generated in `compile_modified_block`,
        # can panic. (Outside any callee, whose effects are already incorporated).
        # TODO We could do better, i.e. panics can only occur if some (indirect) callee
        # is a custom-modifier that manipulates the array (using `array.take()`),
        # but for now we conservatively assume panics can occur.
        ENGINE.register_effects(ctx.current_caller, [Effect.PANIC])

    func_ty = check_modified_block_signature(modified_block, checked_cfg.input_tys)

    checked_modifier = CheckedModifiedBlock(
        block_name,
        checked_cfg,
        func_ty,
        captured,
        modified_block.modifiers,
        **dict(ast.iter_fields(modified_block)),
    )
    return with_loc(modified_block, checked_modifier)


def _body_input(name: str, place: Place) -> Variable:
    """Returns the variable through which a captured place is passed to the body."""
    if isinstance(place, Variable):
        return _set_inout_if_non_copyable(place)
    flags = InputFlags.NoFlags if place.ty.copyable else InputFlags.Inout
    return Variable(name, place.ty, place.defined_at, flags)


def _set_inout_if_non_copyable(var: Variable) -> Variable:
    """Set the `inout` flag if the variable is non-copyable."""
    if not var.ty.copyable:
        return var.add_flags(InputFlags.Inout)
    return var.remove_flags(InputFlags.Inout)


class _BodyTransformer(ast.NodeTransformer):
    """Traverses the body of a modified block, including nested modified blocks."""

    def visit_cfg(self, cfg: CFG) -> None:
        for bb in cfg.bbs:
            bb.statements = [self.visit(stmt) for stmt in bb.statements]
            if bb.branch_pred is not None:
                bb.branch_pred = self.visit(bb.branch_pred)

    def visit_ModifiedBlock(self, node: ModifiedBlock) -> ModifiedBlock:
        for modifier in [*node.control, *node.power]:
            self.visit(modifier)
        self.visit_cfg(node.cfg)
        return node

    def visit_ComptimeExpr(self, node: ComptimeExpr) -> ComptimeExpr:
        # Names inside comptime expressions don't refer to local variables
        return node


def _project(place: Place, step: str | int) -> Place | None:
    """Projects a place onto a struct field (`str`) or a tuple element (`int`)."""
    match place.ty, step:
        case StructType() as ty, str() if step in ty.field_dict:
            return FieldAccess(place, ty.field_dict[step], None)
        case TupleType() as ty, int() if 0 <= step < len(ty.element_types):
            return TupleAccess(place, ty.element_types[step], step, None)
    return None


def _projection(node: ast.expr, candidates: Mapping[str, Variable]) -> Place | None:
    """Returns the place described by a chain of struct field accesses and constant
    tuple indices on one of the candidate variables, e.g. `s.x[0].y`."""
    steps: list[str | int] = []
    while isinstance(node, ast.Attribute | ast.Subscript):
        match node:
            case ast.Attribute(attr=attr):
                steps.append(attr)
            case ast.Subscript(slice=ast.Constant(value=int(idx))):
                steps.append(idx)
            case _:
                return None
        node = node.value
    if not isinstance(node, ast.Name) or node.id not in candidates:
        return None
    place: Place | None = candidates[node.id]
    for step in reversed(steps):
        if place is None:
            return None
        place = _project(place, step)
    return place


class _ProjectionCollector(_BodyTransformer):
    """Collects the projections of the candidate variables that are accessed in the
    body, as well as the variables that must be captured as a whole."""

    #: The struct and tuple variables that are candidates for projection capture
    candidates: Mapping[str, Variable]
    #: The projections that are accessed in the body
    projections: dict[PlaceId, Place]
    #: Variables that must be captured as a whole
    whole: set[str]

    def __init__(self, candidates: Mapping[str, Variable]) -> None:
        self.candidates = candidates
        self.projections: dict[PlaceId, Place] = {}
        self.whole: set[str] = set()

    def _mark_whole(self, node: ast.expr) -> None:
        while isinstance(node, ast.Attribute | ast.Subscript):
            node = node.value
        if isinstance(node, ast.Name) and node.id in self.candidates:
            self.whole.add(node.id)

    def visit_Name(self, node: ast.Name) -> ast.Name:
        # Any use of the variable that isn't a projection requires the whole value
        self._mark_whole(node)
        return node

    def _visit_projection(self, node: ast.Attribute | ast.Subscript) -> ast.expr:
        if not isinstance(node.ctx, ast.Load):
            # Assignments to (parts of) projections require capturing the whole variable
            self._mark_whole(node)
        elif place := _projection(node, self.candidates):
            self.projections[place.id] = place
            return node
        self.generic_visit(node)
        return node

    visit_Attribute = visit_Subscript = _visit_projection

    def visit_NestedFunctionDef(self, node: NestedFunctionDef) -> NestedFunctionDef:
        # To be safe, nested functions always capture whole variables
        for n in ast.walk(node):
            if isinstance(n, ast.Name):
                self.visit_Name(n)
        return node


class _ProjectionRewriter(_BodyTransformer):
    """Replaces accesses to the captured projections with fresh variables."""

    #: The struct and tuple variables that are candidates for projection capture
    candidates: Mapping[str, Variable]
    #: The projections to replace with fresh variables
    captured: Mapping[PlaceId, Place]

    def __init__(
        self, candidates: Mapping[str, Variable], captured: Mapping[PlaceId, Place]
    ) -> None:
        self.candidates = candidates
        self.captured = captured

    def _visit_projection(self, node: ast.Attribute | ast.Subscript) -> ast.expr:
        place = _projection(node, self.candidates)
        if place and place.id in self.captured:
            name = ast.Name(id=str(self.captured[place.id]), ctx=ast.Load())
            set_location_from(name, node)
            return name
        self.generic_visit(node)
        return node

    visit_Attribute = visit_Subscript = _visit_projection

    def visit_NestedFunctionDef(self, node: NestedFunctionDef) -> NestedFunctionDef:
        return node


def _capture_projections(
    cfg: CFG, candidates: Mapping[str, Variable]
) -> dict[str, Place]:
    """Rewrites the body of a modified block such that accesses to struct fields and
    tuple elements of local variables are replaced by fresh variables.

    For example, if a body only uses `s.x` and `t[0][1]`, the occurrences are replaced
    with variables called `s.x` and `t[0][1]` (which can't clash with user-defined
    variables). This allows us to capture only the used parts instead of the whole
    struct or tuple.

    Returns a mapping from the names of the fresh variables to the places they refer
    to.
    """
    collector = _ProjectionCollector(candidates)
    collector.visit_cfg(cfg)

    used = {
        pid: place
        for pid, place in collector.projections.items()
        if place.root.name not in collector.whole
    }
    # If both a place and one of its projections are used, we capture the outer one
    captured = {
        pid: place
        for pid, place in used.items()
        if not any(parent.id in used for parent in parent_places(place))
    }
    _ProjectionRewriter(candidates, captured).visit_cfg(cfg)
    return {str(place): place for place in captured.values()}


def check_modified_block_signature(
    modified_block: ModifiedBlock, input_tys: list[Type]
) -> FunctionType:
    """Check and create the signature of a function definition for a body
    of a `With` block."""
    # We use accumulated_flags here so the block has the correct modifier
    # metadata when it is nested under other modifiers.
    unitary_flags = modified_block.accumulated_flags

    func_ty = FunctionType(
        [
            FuncInput(t, InputFlags.Inout if not t.copyable else InputFlags.NoFlags)
            for t in input_tys
        ],
        NoneType(),
        unitary_flags=unitary_flags,
    )
    return func_ty


def non_copyable_front_others_back[P: Place](v: list[P]) -> list[P]:
    """Reorder variables so that linear ones come first, preserving the relative order
    of linear and non-linear variables."""
    linear_vars = [x for x in v if not x.ty.copyable]
    non_linear_vars = [x for x in v if x.ty.copyable]
    return linear_vars + non_linear_vars
