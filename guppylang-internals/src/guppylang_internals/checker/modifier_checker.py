"""Type checking code for modifiers."""

import ast
from collections.abc import Mapping

from guppylang_internals.ast_util import set_location_from, with_loc
from guppylang_internals.cfg.bb import BB
from guppylang_internals.cfg.cfg import CFG
from guppylang_internals.checker.cfg_checker import check_cfg
from guppylang_internals.checker.core import Context, FieldAccess, Place, Variable
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

    # If the body only accesses some fields of a struct, we capture those fields
    # instead of the whole struct. This allows, for example, using one field of a
    # struct as control while acting on another field inside the body.
    captured_fields = _capture_struct_fields(
        cfg,
        {
            x: ctx.locals[x]
            for x in cfg.live_before[cfg.entry_bb]
            if x in ctx.locals and isinstance(ctx.locals[x].ty, StructType)
        },
    )
    if captured_fields:
        def_ass_before = def_ass_before | captured_fields.keys()
        maybe_ass_before = maybe_ass_before | captured_fields.keys()
        cfg.analyze(def_ass_before, maybe_ass_before, [])

    captured = {
        x: (
            captured_fields[x] if x in captured_fields else ctx.locals[x],
            using_bb.vars.used[x],
        )
        for x, using_bb in cfg.live_before[cfg.entry_bb].items()
        if x in captured_fields or x in ctx.locals
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


def _field_path(
    node: ast.expr, candidates: Mapping[str, Variable]
) -> tuple[str, tuple[str, ...]] | None:
    """Returns the variable name and accessed field names if the node is a chain of
    struct field accesses on one of the candidate variables, e.g. `s.x.y`."""
    attrs = []
    while isinstance(node, ast.Attribute):
        attrs.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name) or node.id not in candidates:
        return None
    path = tuple(reversed(attrs))
    ty = candidates[node.id].ty
    for field_name in path:
        if not isinstance(ty, StructType) or field_name not in ty.field_dict:
            return None
        ty = ty.field_dict[field_name].ty
    return node.id, path


class _FieldUseCollector(_BodyTransformer):
    """Collects the struct fields accessed on the candidate variables and the
    variables that must be captured as a whole."""

    def __init__(self, candidates: Mapping[str, Variable]) -> None:
        self.candidates = candidates
        self.paths: dict[str, set[tuple[str, ...]]] = {}
        self.whole: set[str] = set()

    def _mark_whole(self, node: ast.expr) -> None:
        while isinstance(node, ast.Attribute | ast.Subscript):
            node = node.value
        if isinstance(node, ast.Name) and node.id in self.candidates:
            self.whole.add(node.id)

    def visit_Name(self, node: ast.Name) -> ast.Name:
        # Any use of the variable that isn't a field access requires the whole value
        if node.id in self.candidates:
            self.whole.add(node.id)
        return node

    def visit_Attribute(self, node: ast.Attribute) -> ast.Attribute:
        if not isinstance(node.ctx, ast.Load):
            # Assignments to (parts of) fields require capturing the whole variable
            self._mark_whole(node)
        elif fp := _field_path(node, self.candidates):
            x, path = fp
            self.paths.setdefault(x, set()).add(path)
            return node
        self.generic_visit(node)
        return node

    def visit_Subscript(self, node: ast.Subscript) -> ast.Subscript:
        if not isinstance(node.ctx, ast.Load):
            self._mark_whole(node)
        self.generic_visit(node)
        return node

    def visit_NestedFunctionDef(self, node: NestedFunctionDef) -> NestedFunctionDef:
        # To be safe, nested functions always capture whole variables
        for n in ast.walk(node):
            if isinstance(n, ast.Name):
                self.visit_Name(n)
        return node


class _FieldUseRewriter(_BodyTransformer):
    """Replaces struct field accesses with the corresponding fresh variables."""

    def __init__(
        self,
        candidates: Mapping[str, Variable],
        captured: Mapping[str, set[tuple[str, ...]]],
    ) -> None:
        self.candidates = candidates
        self.captured = captured

    def visit_Attribute(self, node: ast.Attribute) -> ast.expr:
        fp = _field_path(node, self.candidates)
        if fp and fp[1] in self.captured.get(fp[0], ()):
            name = ast.Name(id=".".join([fp[0], *fp[1]]), ctx=ast.Load())
            set_location_from(name, node)
            return name
        self.generic_visit(node)
        return node

    def visit_NestedFunctionDef(self, node: NestedFunctionDef) -> NestedFunctionDef:
        return node


def _capture_struct_fields(
    cfg: CFG, candidates: Mapping[str, Variable]
) -> dict[str, Place]:
    """Rewrites the body of a modified block such that accesses to fields of struct
    variables are replaced by fresh variables.

    For example, if a body only uses `s.x` and `s.y.z`, the occurrences are replaced
    with variables called `s.x` and `s.y.z` (which can't clash with user-defined
    variables). This allows us to capture only the used fields instead of the whole
    struct.

    Returns a mapping from the names of the fresh variables to the places they refer
    to.
    """
    collector = _FieldUseCollector(candidates)
    collector.visit_cfg(cfg)

    # If both a field and one of its sub-fields are used, we capture the outer one
    captured_paths = {
        x: {p for p in paths if not any(p[: len(q)] == q != p for q in paths)}
        for x, paths in collector.paths.items()
        if x not in collector.whole
    }
    _FieldUseRewriter(candidates, captured_paths).visit_cfg(cfg)

    captured: dict[str, Place] = {}
    for x, paths in captured_paths.items():
        for path in paths:
            place: Place = candidates[x]
            for field_name in path:
                assert isinstance(place.ty, StructType)
                place = FieldAccess(place, place.ty.field_dict[field_name], None)
            captured[".".join([x, *path])] = place
    return captured


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
