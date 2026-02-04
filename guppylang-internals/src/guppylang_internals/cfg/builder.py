import ast
import copy
import itertools
from collections.abc import Iterator
from dataclasses import dataclass
from typing import ClassVar, NamedTuple

from guppylang_internals.ast_util import (
    AstVisitor,
    ContextAdjuster,
    find_nodes,
    loop_controls_in_loop,
    return_nodes_in_ast,
    set_location_from,
    template_replace,
    with_loc,
)
from guppylang_internals.cfg.bb import BB, BBStatement
from guppylang_internals.cfg.cfg import CFG
from guppylang_internals.checker.core import Globals
from guppylang_internals.checker.errors.generic import (
    ExpectedError,
    UnexpectedInWithBlockError,
    UnknownModifierError,
    UnsupportedError,
)
from guppylang_internals.checker.errors.type_errors import WrongNumberOfArgsError
from guppylang_internals.diagnostic import Error
from guppylang_internals.error import GuppyError, InternalGuppyError
from guppylang_internals.experimental import (
    check_lists_enabled,
    check_modifiers_enabled,
)
from guppylang_internals.nodes import (
    ComptimeExpr,
    Control,
    Dagger,
    DesugaredGenerator,
    DesugaredGeneratorExpr,
    DesugaredListComp,
    IterNext,
    MakeIter,
    ModifiedBlock,
    Modifier,
    NestedFunctionDef,
    Power,
)
from guppylang_internals.span import Span, to_span
from guppylang_internals.tys.ty import NoneType, UnitaryFlags

# In order to build expressions, need an endless stream of unique temporary variables
# to store intermediate results
tmp_vars: Iterator[str] = (f"%tmp{i}" for i in itertools.count())


def is_tmp_var(x: str) -> bool:
    """Checks if a name corresponds to a temporary variable."""
    return x.startswith("%tmp")


class Jumps(NamedTuple):
    """Holds jump targets for return, continue, and break during CFG construction."""

    return_bb: BB
    continue_bb: BB | None
    break_bb: BB | None


@dataclass(frozen=True)
class UnreachableError(Error):
    title: ClassVar[str] = "Unreachable"
    span_label: ClassVar[str] = "This code is not reachable"


class CFGBuilder(AstVisitor[BB | None]):
    """Constructs a CFG from ast nodes."""

    cfg: CFG
    globals: Globals

    def build(
        self,
        nodes: list[ast.stmt],
        returns_none: bool,
        globals: Globals,
        unitary_flags: UnitaryFlags = UnitaryFlags.NoFlags,
    ) -> CFG:
        """Builds a CFG from a list of ast nodes.

        We also require the expected number of return ports for the whole CFG. This is
        needed to translate return statements into assignments of dummy return
        variables.
        """
        self.cfg = CFG()
        self.cfg.unitary_flags = unitary_flags
        self.globals = globals

        final_bb = self.visit_stmts(
            nodes, self.cfg.entry_bb, Jumps(self.cfg.exit_bb, None, None)
        )

        # Compute reachable BBs
        self.cfg.update_reachable()

        # If we're still in a basic block after compiling the whole body, we have to add
        # an implicit void return
        if final_bb is not None:
            self.cfg.link(final_bb, self.cfg.exit_bb)
            if final_bb.reachable:
                self.cfg.exit_bb.reachable = True
                if not returns_none:
                    raise GuppyError(ExpectedError(nodes[-1], "return statement"))

        # Prune the CFG such that there are no jumps from unreachable code back into
        # reachable code. Otherwise, unreachable code could lead to unnecessary type
        # checking errors, e.g. if unreachable code changes the type of a variable.
        for bb in self.cfg.bbs:
            if not bb.reachable:
                for succ in list(bb.successors):
                    if succ.reachable:
                        bb.successors.remove(succ)
                        succ.predecessors.remove(bb)
            # Similarly, if a BB is reachable, then there is no need to hold on to dummy
            # jumps into it. Dummy jumps are only needed to propagate type information
            # into and between unreachable BBs
            else:
                for pred in bb.dummy_predecessors:
                    pred.dummy_successors.remove(bb)
                bb.dummy_predecessors = []

        return self.cfg

    def visit_stmts(self, nodes: list[ast.stmt], bb: BB, jumps: Jumps) -> BB | None:
        prev_bb = bb
        bb_opt: BB | None = bb
        next_functional = False
        for node in nodes:
            # If the previous statement jumped, then all following statements are
            # unreachable. Just create a new dummy BB and keep going so we can still
            # check the unreachable code.
            if bb_opt is None:
                bb_opt = self.cfg.new_bb()
                self.cfg.dummy_link(prev_bb, bb_opt)
            if is_functional_annotation(node):
                next_functional = True
                continue

            if next_functional:
                # TODO: This should be an assertion that the Hugr can be un-flattened
                raise NotImplementedError
                next_functional = False
            else:
                prev_bb, bb_opt = bb_opt, self.visit(node, bb_opt, jumps)
        return bb_opt

    def _build_node_value(self, node: BBStatement, bb: BB) -> BB:
        """Utility method for building a nodes `value` expression, if available.

        Builds the expression and mutates `node.value` to point to the built expression.
        Returns the BB in which the expression is available.
        """
        if (
            not isinstance(node, NestedFunctionDef | ModifiedBlock)
            and node.value is not None
        ):
            node.value, bb = ExprBuilder.build(node.value, self.cfg, bb)
        return bb

    def _build_node_targets(self, node: BBStatement, bb: BB) -> BB:
        """Utility method for building a nodes `target` or `targets` expressions,
        depending on the node type.

        Builds the expressions and mutates the elements of `node.targets` to point to
        the built expressions. Returns the BB in which the expressions are available.
        """
        if isinstance(node, ast.Assign):
            for i, target in enumerate(node.targets):
                node.targets[i], bb = ExprBuilder.build(target, self.cfg, bb)
        elif isinstance(node, ast.AugAssign | ast.AnnAssign):
            new_target, bb = ExprBuilder.build(node.target, self.cfg, bb)
            if not isinstance(new_target, ast.Name | ast.Attribute | ast.Subscript):
                raise InternalGuppyError("Unexpected type for built expression.")
            node.target = new_target
        return bb

    def visit_Assign(self, node: ast.Assign, bb: BB, jumps: Jumps) -> BB | None:
        bb = self._build_node_value(node, bb)
        bb = self._build_node_targets(node, bb)
        bb.statements.append(node)
        return bb

    def visit_AugAssign(self, node: ast.AugAssign, bb: BB, jumps: Jumps) -> BB | None:
        bb = self._build_node_value(node, bb)
        bb = self._build_node_targets(node, bb)
        bb.statements.append(node)
        return bb

    def visit_AnnAssign(self, node: ast.AnnAssign, bb: BB, jumps: Jumps) -> BB | None:
        bb = self._build_node_value(node, bb)
        bb = self._build_node_targets(node, bb)
        bb.statements.append(node)
        return bb

    def visit_Expr(self, node: ast.Expr, bb: BB, jumps: Jumps) -> BB | None:
        # This is an expression statement where the value is discarded
        node.value, bb = ExprBuilder.build(node.value, self.cfg, bb)
        # We don't add it to the BB if it's just a temporary variable. This will be the
        # case if it's a branching expression, e.g. `42 if cond else False`. In that
        # example the type mismatch is actually fine since the result is never used. To
        # achieve this behaviour we must not add the temporary result variable to the BB
        if not isinstance(node.value, ast.Name) or not is_tmp_var(node.value.id):
            bb.statements.append(node)
        return bb

    def visit_If(self, node: ast.If, bb: BB, jumps: Jumps) -> BB | None:
        then_bb, else_bb = self.cfg.new_bb(), self.cfg.new_bb()
        BranchBuilder.add_branch(node.test, self.cfg, bb, then_bb, else_bb)
        then_bb = self.visit_stmts(node.body, then_bb, jumps)
        else_bb = self.visit_stmts(node.orelse, else_bb, jumps)
        # We need to handle different cases depending on whether branches jump (i.e.
        # return, continue, or break)
        if then_bb is None:
            # If branch jumps: We continue in the BB of the else branch
            return else_bb
        elif else_bb is None:
            # Else branch jumps: We continue in the BB of the if branch
            return then_bb
        else:
            # No branch jumps: We have to merge the control flow
            return self.cfg.new_bb(then_bb, else_bb)

    def visit_While(self, node: ast.While, bb: BB, jumps: Jumps) -> BB | None:
        head_bb = self.cfg.new_bb(bb)
        body_bb, tail_bb = self.cfg.new_bb(), self.cfg.new_bb()
        BranchBuilder.add_branch(node.test, self.cfg, head_bb, body_bb, tail_bb)

        new_jumps = Jumps(
            return_bb=jumps.return_bb, continue_bb=head_bb, break_bb=tail_bb
        )
        body_end_bb = self.visit_stmts(node.body, body_bb, new_jumps)

        # Go back to the head (but only the body doesn't do its jumping)
        if body_end_bb is not None:
            self.cfg.link(body_end_bb, head_bb)

        # Continue compilation in the tail. This should even happen if the body does
        # its own jumps since the body is not guaranteed to execute
        return tail_bb

    def visit_For(self, node: ast.For, bb: BB, jumps: Jumps) -> BB | None:
        template = """
            it = make_iter
            while True:
                res = iter_next
                if not res.is_some():
                    res.unwrap_nothing()
                    break
                x, it = res.unwrap()
                body
        """

        it = make_var(next(tmp_vars), node.iter)
        res = make_var(next(tmp_vars), node.iter)
        new_nodes = template_replace(
            template,
            node.iter,
            it=it,
            res=res,
            x=node.target,
            make_iter=with_loc(node.iter, MakeIter(value=node.iter, origin_node=node)),
            iter_next=with_loc(node.iter, IterNext(value=it)),
            body=node.body,
        )
        return self.visit_stmts(new_nodes, bb, jumps)

    def visit_Continue(self, node: ast.Continue, bb: BB, jumps: Jumps) -> BB | None:
        if not jumps.continue_bb:
            raise InternalGuppyError("Continue BB not defined")
        self.cfg.link(bb, jumps.continue_bb)
        return None

    def visit_Break(self, node: ast.Break, bb: BB, jumps: Jumps) -> BB | None:
        if not jumps.break_bb:
            raise InternalGuppyError("Break BB not defined")
        self.cfg.link(bb, jumps.break_bb)
        return None

    def visit_Return(self, node: ast.Return, bb: BB, jumps: Jumps) -> BB | None:
        bb = self._build_node_value(node, bb)
        bb.statements.append(node)
        self.cfg.link(bb, jumps.return_bb)
        return None

    def visit_Pass(self, node: ast.Pass, bb: BB, jumps: Jumps) -> BB | None:
        return bb

    def visit_FunctionDef(
        self, node: ast.FunctionDef, bb: BB, jumps: Jumps
    ) -> BB | None:
        from guppylang_internals.checker.func_checker import (
            check_signature,
            parse_function_with_docstring,
        )

        node, docstring = parse_function_with_docstring(node)

        func_ty = check_signature(node, self.globals)
        returns_none = isinstance(func_ty.output, NoneType)
        # No UnitaryFlags are assigned to nested functions
        cfg = CFGBuilder().build(node.body, returns_none, self.globals)

        new_node = NestedFunctionDef(
            cfg,
            func_ty,
            docstring=docstring,
            **dict(ast.iter_fields(node)),
        )
        set_location_from(new_node, node)
        bb.statements.append(new_node)
        return bb

    def visit_With(self, node: ast.With, bb: BB, jumps: Jumps) -> BB | None:
        check_modifiers_enabled(node)
        self._validate_modified_block(node)

        cfg = CFGBuilder().build(node.body, True, self.globals)
        new_node = ModifiedBlock(
            cfg=cfg,
            **dict(ast.iter_fields(node)),
        )

        for item in node.items:
            item.context_expr, bb = ExprBuilder.build(item.context_expr, self.cfg, bb)
            modifier = self._handle_withitem(item)
            new_node.push_modifier(modifier)

        # FIXME: Currently, the unitary flags is not set correctly if there are nested
        # `with` blocks. This is because the outer block's unitary flags are not
        # propagated to the outer block. The following line should calculate the sum
        # of the unitary flags of the outer block and modifiers applied in this
        # `with` block.
        cfg.unitary_flags = new_node.flags()

        set_location_from(new_node, node)
        bb.statements.append(new_node)
        return bb

    def _handle_withitem(self, node: ast.withitem) -> Modifier:
        # Check that `as` notation is not used
        if node.optional_vars is not None:
            span = Span(
                to_span(node.context_expr).start, to_span(node.optional_vars).end
            )
            raise GuppyError(UnsupportedError(span, "`as` expression", singular=True))

        e = node.context_expr
        modifier: Modifier
        match e:
            case ast.Name(id="dagger"):
                modifier = Dagger(e)
            case ast.Call(func=ast.Name(id="dagger")):
                if len(e.args) != 0:
                    span = Span(to_span(e.args[0]).start, to_span(e.args[-1]).end)
                    raise GuppyError(WrongNumberOfArgsError(span, 0, len(e.args)))
                modifier = Dagger(e)
            case ast.Call(func=ast.Name(id="control")):
                if len(e.args) == 0:
                    span = Span(to_span(e.func).end, to_span(e).end)
                    raise GuppyError(WrongNumberOfArgsError(span, 1, len(e.args)))
                modifier = Control(e, e.args)
            case ast.Call(func=ast.Name(id="power")):
                if len(e.args) == 0:
                    span = Span(to_span(e.func).end, to_span(e).end)
                    raise GuppyError(WrongNumberOfArgsError(span, 1, len(e.args)))
                elif len(e.args) != 1:
                    span = Span(to_span(e.args[1]).start, to_span(e.args[-1]).end)
                    raise GuppyError(WrongNumberOfArgsError(span, 1, len(e.args)))
                modifier = Power(e, e.args[0])
            case _:
                raise GuppyError(UnknownModifierError(e))
        return modifier

    def _validate_modified_block(self, node: ast.With) -> None:
        # Check if the body contains a return statement.
        return_in_body = return_nodes_in_ast(node)
        if len(return_in_body) != 0:
            err = UnexpectedInWithBlockError(return_in_body[0], "return", "Return")
            span = Span(
                to_span(node.items[0].context_expr).start,
                to_span(node.items[-1].context_expr).end,
            )
            err.add_sub_diagnostic(UnexpectedInWithBlockError.Modifier(span))
            raise GuppyError(err)

        loop_controls_in_body = loop_controls_in_loop(node)
        if len(loop_controls_in_body) != 0:
            lc = loop_controls_in_body[0]
            kind = lc.__class__.__name__
            err = UnexpectedInWithBlockError(lc, "loop control", kind)
            span = Span(
                to_span(node.items[0].context_expr).start,
                to_span(node.items[-1].context_expr).end,
            )
            err.add_sub_diagnostic(UnexpectedInWithBlockError.Modifier(span))
            raise GuppyError(err)

    def generic_visit(self, node: ast.AST, bb: BB, jumps: Jumps) -> BB | None:
        # When adding support for new statements, we have to remember to use the
        # ExprBuilder to transform all included expressions!
        raise GuppyError(UnsupportedError(node, "This statement", singular=True))


class ExprBuilder(ast.NodeTransformer):
    """Builds an expression into a basic block."""

    cfg: CFG
    bb: BB

    def __init__(self, cfg: CFG, start_bb: BB) -> None:
        self.cfg = cfg
        self.bb = start_bb

    @staticmethod
    def build(node: ast.expr, cfg: CFG, bb: BB) -> tuple[ast.expr, BB]:
        """Builds an expression into a CFG.

        The expression may be transformed and new basic blocks may be created (for
        example for `... if ... else ...` expressions). Returns the new expression and
        the final basic block in which the expression can be used."""
        builder = ExprBuilder(cfg, bb)
        return builder.visit(node), builder.bb

    @classmethod
    def _tmp_assign(cls, tmp_name: str, value: ast.expr, bb: BB) -> None:
        """Adds a temporary variable assignment to a basic block."""
        lhs = make_var(tmp_name, value)
        bb.statements.append(make_assign([lhs], value))

    def visit_Name(self, node: ast.Name) -> ast.Name:
        return node

    def visit_NamedExpr(self, node: ast.NamedExpr) -> ast.Name:
        # This is an assignment expression, e.g. `x := 42`. We turn it into an
        # assignment statement and replace the expression with `x`.
        if not isinstance(node.target, ast.Name):
            raise InternalGuppyError(f"Unexpected assign target: {node.target}")
        assign = ast.Assign(
            targets=[copy.deepcopy(node.target)], value=self.visit(node.value)
        )
        set_location_from(assign, node)
        self.bb.statements.append(assign)
        return node.target

    def visit_IfExp(self, node: ast.IfExp) -> ast.Name:
        if_bb, else_bb = self.cfg.new_bb(), self.cfg.new_bb()
        BranchBuilder.add_branch(node.test, self.cfg, self.bb, if_bb, else_bb)

        if_expr, if_bb = self.build(node.body, self.cfg, if_bb)
        else_expr, else_bb = self.build(node.orelse, self.cfg, else_bb)

        # Assign the result to a temporary variable
        tmp = next(tmp_vars)
        self._tmp_assign(tmp, if_expr, if_bb)
        self._tmp_assign(tmp, else_expr, else_bb)

        # Merge the temporary variables in a new BB
        merge_bb = self.cfg.new_bb(if_bb, else_bb)
        self.bb = merge_bb

        # The final value is stored in the temporary variable
        return make_var(tmp, node)

    def visit_ListComp(self, node: ast.ListComp) -> DesugaredListComp:
        check_lists_enabled(node)
        generators, elt = desugar_comprehension(node.generators, node.elt, node)
        return with_loc(node, DesugaredListComp(elt=elt, generators=generators))

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> DesugaredGeneratorExpr:
        generators, elt = desugar_comprehension(node.generators, node.elt, node)
        return with_loc(node, DesugaredGeneratorExpr(elt=elt, generators=generators))

    def visit_Call(self, node: ast.Call) -> ast.AST:
        return is_comptime_expression(node) or self.generic_visit(node)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ast.AST:
        # Desugar negated numeric constants into constants
        match node.op, node.operand:
            case ast.USub(), ast.Constant(value=float(v) | int(v)) as const:
                const.value = -v
                return with_loc(node, const)
            case _:
                return self.generic_visit(node)

    def generic_visit(self, node: ast.AST) -> ast.AST:
        # Short-circuit expressions must be built using the `BranchBuilder`. However, we
        # can turn them into regular expressions by assigning True/False to a temporary
        # variable and merging the control-flow
        if is_short_circuit_expr(node):
            assert isinstance(node, ast.expr)
            true_bb, false_bb = self.cfg.new_bb(), self.cfg.new_bb()
            BranchBuilder.add_branch(node, self.cfg, self.bb, true_bb, false_bb)
            true_const = ast.Constant(value=True)
            false_const = ast.Constant(value=False)
            set_location_from(true_const, node)
            set_location_from(false_const, node)
            tmp = next(tmp_vars)
            self._tmp_assign(tmp, true_const, true_bb)
            self._tmp_assign(tmp, false_const, false_bb)
            merge_bb = self.cfg.new_bb(true_bb, false_bb)
            self.bb = merge_bb
            return make_var(tmp, node)
        # For all other expressions, just recurse deeper with the node transformer
        return super().generic_visit(node)


class BranchBuilder(AstVisitor[None]):
    """Builds an expression and does branching based on the value.

    This builder should be used to handle all branching on boolean values since it
    handles short-circuit evaluation etc.
    """

    cfg: CFG

    def __init__(self, cfg: CFG):
        """Creates a new `BranchBuilder`."""
        self.cfg = cfg

    @staticmethod
    def add_branch(node: ast.expr, cfg: CFG, bb: BB, true_bb: BB, false_bb: BB) -> None:
        """Builds an expression and branches to `true_bb` or `false_bb`, depending on
        the truth value of the expression."""
        builder = BranchBuilder(cfg)
        builder.visit(node, bb, true_bb, false_bb)

    def visit_Constant(
        self, node: ast.Constant, bb: BB, true_bb: BB, false_bb: BB
    ) -> None:
        # Branching on `True` or `False` constant should be unconditional
        if isinstance(node.value, bool):
            self.cfg.link(bb, true_bb if node.value else false_bb)
            self.cfg.dummy_link(bb, false_bb if node.value else true_bb)
        else:
            self.generic_visit(node, bb, true_bb, false_bb)

    def visit_BoolOp(self, node: ast.BoolOp, bb: BB, true_bb: BB, false_bb: BB) -> None:
        # Add short-circuit evaluation of boolean expression. If there are more than 2
        # operators, we turn the flat operator list into a right-nested tree to allow
        # for recursive processing.
        assert len(node.values) > 1
        if len(node.values) > 2:
            r = ast.BoolOp(
                op=node.op,
                values=node.values[1:],
                lineno=node.values[0].lineno,
                col_offset=node.values[0].col_offset,
                end_lineno=node.values[-1].end_lineno,
                end_col_offset=node.values[-1].end_col_offset,
            )
            node.values = [node.values[0], r]
        [left, right] = node.values

        extra_bb = self.cfg.new_bb()
        assert type(node.op) in [ast.And, ast.Or]
        if isinstance(node.op, ast.And):
            self.visit(left, bb, extra_bb, false_bb)
        elif isinstance(node.op, ast.Or):
            self.visit(left, bb, true_bb, extra_bb)
        self.visit(right, extra_bb, true_bb, false_bb)

    def visit_UnaryOp(
        self, node: ast.UnaryOp, bb: BB, true_bb: BB, false_bb: BB
    ) -> None:
        # For `not` operator, we can just switch `true_bb` and `false_bb`
        if isinstance(node.op, ast.Not):
            self.visit(node.operand, bb, false_bb, true_bb)
        else:
            self.generic_visit(node, bb, true_bb, false_bb)

    def visit_Compare(
        self, node: ast.Compare, bb: BB, true_bb: BB, false_bb: BB
    ) -> None:
        # Support chained comparisons, e.g. `x <= 5 < y` by compiling to `x <= 5 and
        # 5 < y`. This way we get short-circuit evaluation for free.
        if len(node.comparators) > 1:
            comparators = [node.left, *node.comparators]
            values = [
                ast.Compare(
                    left=left,
                    ops=[op],
                    comparators=[right],
                    lineno=left.lineno,
                    col_offset=left.col_offset,
                    end_lineno=right.end_lineno,
                    end_col_offset=right.end_col_offset,
                )
                for left, op, right in zip(
                    comparators[:-1], node.ops, comparators[1:], strict=True
                )
            ]
            conj = ast.BoolOp(op=ast.And(), values=values)  # type: ignore[arg-type]
            set_location_from(conj, node)
            self.visit_BoolOp(conj, bb, true_bb, false_bb)
        else:
            self.generic_visit(node, bb, true_bb, false_bb)

    def visit_IfExp(self, node: ast.IfExp, bb: BB, true_bb: BB, false_bb: BB) -> None:
        then_bb, else_bb = self.cfg.new_bb(), self.cfg.new_bb()
        self.visit(node.test, bb, then_bb, else_bb)
        self.visit(node.body, then_bb, true_bb, false_bb)
        self.visit(node.orelse, else_bb, true_bb, false_bb)

    def generic_visit(self, node: ast.expr, bb: BB, true_bb: BB, false_bb: BB) -> None:
        # We can always fall back to building the node as a regular expression and using
        # the result as a branch predicate
        pred, bb = ExprBuilder.build(node, self.cfg, bb)
        bb.branch_pred = pred
        self.cfg.link(bb, false_bb)
        self.cfg.link(bb, true_bb)


def desugar_comprehension(
    generators: list[ast.comprehension], elt: ast.expr, node: ast.AST
) -> tuple[list[DesugaredGenerator], ast.expr]:
    """Helper function to desugar a comprehension node."""
    # Check for illegal expressions
    illegals = find_nodes(is_illegal_in_list_comp, node)
    if illegals:
        err = UnsupportedError(
            illegals[0],
            "This expression",
            singular=True,
            unsupported_in="a list comprehension",
        )
        raise GuppyError(err)

    # The check above ensures that the comprehension doesn't contain any control-flow
    # expressions. Thus, we can use a dummy `ExprBuilder` to desugar the insides.
    # TODO: Refactor so that desugaring is separate from control-flow building
    dummy_cfg = CFG()
    builder = ExprBuilder(dummy_cfg, dummy_cfg.entry_bb)

    # Desugar into statements that create the iterator, check for a next element,
    # get the next element, and finalise the iterator.
    gens = []
    for g in generators:
        if g.is_async:
            raise GuppyError(UnsupportedError(g, "Async generators"))
        g.iter = builder.visit(g.iter)
        it = make_var(next(tmp_vars), g.iter)
        desugared = DesugaredGenerator(
            iter=it,
            iter_assign=make_assign(
                [it], with_loc(it, MakeIter(value=g.iter, origin_node=node))
            ),
            next_call=with_loc(it, IterNext(value=it)),
            target=g.target,
            ifs=g.ifs,
            used_outer_places=[],
        )
        gens.append(desugared)

    elt = builder.visit(elt)
    return gens, elt


def is_functional_annotation(stmt: ast.stmt) -> bool:
    """Returns `True` iff the given statement is the functional pseudo-decorator.

    Pseudo-decorators are built using the matmul operator `@`, i.e. `_@functional`.
    """
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.BinOp):
        op = stmt.value
        if (
            isinstance(op.op, ast.MatMult)
            and isinstance(op.left, ast.Name)
            and isinstance(op.right, ast.Name)
        ):
            return op.left.id == "_" and op.right.id == "functional"
    return False


@dataclass(frozen=True)
class EmptyComptimeExprError(Error):
    title: ClassVar[str] = "Invalid comptime expression"
    span_label: ClassVar[str] = "Comptime expression requires an argument"


def is_comptime_expression(node: ast.AST) -> ComptimeExpr | None:
    """Checks if the given node is a `comptime(...)` expression and turns it into
    a `ComptimeExpr` AST node.

    Also accepts the `py(...)` alias for `comptime` expressions.

    Otherwise, returns `None`.
    """
    if isinstance(node, ComptimeExpr):
        return node

    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in ("py", "comptime")
    ):
        match node.args:
            case []:
                raise GuppyError(EmptyComptimeExprError(node))
            case [arg]:
                pass
            case args:
                arg = with_loc(node, ast.Tuple(elts=args, ctx=ast.Load))  # type: ignore[arg-type]
        return with_loc(node, ComptimeExpr(arg))
    return None


def is_short_circuit_expr(node: ast.AST) -> bool:
    """Checks if an expression uses short-circuiting.

    Those expressions *must* be compiled using the `BranchBuilder`.
    """
    return isinstance(node, ast.BoolOp) or (
        isinstance(node, ast.Compare) and len(node.comparators) > 1
    )


def is_illegal_in_list_comp(node: ast.AST) -> bool:
    """Checks if an expression is illegal to use in a list comprehension."""
    return isinstance(node, ast.IfExp | ast.NamedExpr) or is_short_circuit_expr(node)


def make_var(name: str, loc: ast.AST | None = None) -> ast.Name:
    """Creates an `ast.Name` node."""
    node = ast.Name(id=name, ctx=ast.Load)  # type: ignore[arg-type]
    if loc is not None:
        set_location_from(node, loc)
    return node


def make_assign(lhs: list[ast.AST], value: ast.expr) -> ast.Assign:
    """Creates an `ast.Assign` node."""
    assert len(lhs) > 0
    adjuster = ContextAdjuster(ast.Store())
    lhs = [adjuster.visit(expr) for expr in lhs]
    if len(lhs) == 1:
        target = lhs[0]
    else:
        target = with_loc(
            value,
            ast.Tuple(elts=lhs, ctx=ast.Store()),  # type: ignore[arg-type]
        )
    return with_loc(value, ast.Assign(targets=[target], value=value))  # type: ignore[list-item]
