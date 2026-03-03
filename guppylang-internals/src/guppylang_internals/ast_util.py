import ast
import textwrap
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, Optional, TypeVar, cast

if TYPE_CHECKING:
    from guppylang_internals.tys.ty import Type

AstNode = (
    ast.AST
    | ast.operator
    | ast.expr
    | ast.arg
    | ast.stmt
    | ast.Name
    | ast.keyword
    | ast.FunctionDef
)

T = TypeVar("T", covariant=True)


class AstVisitor(Generic[T]):
    """
    Note: This class is based on the implementation of `ast.NodeVisitor` but
    allows extra arguments to be passed to the `visit` functions.

    Original documentation:

    A node visitor base class that walks the abstract syntax tree and calls a
    visitor function for every node found.  This function may return a value
    which is forwarded by the `visit` method.

    This class is meant to be subclassed, with the subclass adding visitor
    methods.

    Per default the visitor functions for the nodes are ``'visit_'`` +
    class name of the node.  So a `TryFinally` node visit function would
    be `visit_TryFinally`.  This behavior can be changed by overriding
    the `visit` method.  If no visitor function exists for a node
    (return value `None`) the `generic_visit` visitor is used instead.

    Don't use the `NodeVisitor` if you want to apply changes to nodes during
    traversing.  For this a special visitor exists (`NodeTransformer`) that
    allows modifications.
    """

    def visit(self, node: Any, *args: Any, **kwargs: Any) -> T:
        """Visit a node."""
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, *args, **kwargs)

    def generic_visit(self, node: Any, *args: Any, **kwargs: Any) -> T:
        """Called if no explicit visitor function exists for a node."""
        raise NotImplementedError(f"visit_{node.__class__.__name__} is not implemented")


class AstSearcher(ast.NodeVisitor):
    """Visitor that searches for occurrences of specific nodes in an AST."""

    matcher: Callable[[ast.AST], bool]
    dont_recurse_into: set[type[ast.AST]]
    found: list[ast.AST]
    is_first_node: bool

    def __init__(
        self,
        matcher: Callable[[ast.AST], bool],
        dont_recurse_into: set[type[ast.AST]] | None = None,
    ) -> None:
        self.matcher = matcher
        self.dont_recurse_into = dont_recurse_into or set()
        self.found = []
        self.is_first_node = True

    def generic_visit(self, node: ast.AST) -> None:
        if self.matcher(node):
            self.found.append(node)
        if self.is_first_node or type(node) not in self.dont_recurse_into:
            self.is_first_node = False
            super().generic_visit(node)


def find_nodes(
    matcher: Callable[[ast.AST], bool],
    node: ast.AST,
    dont_recurse_into: set[type[ast.AST]] | None = None,
) -> list[ast.AST]:
    """Returns all nodes in the AST that satisfy the matcher."""
    v = AstSearcher(matcher, dont_recurse_into)
    v.visit(node)
    return v.found


def name_nodes_in_ast(node: Any) -> list[ast.Name]:
    """Returns all `Name` nodes occurring in an AST."""
    found = find_nodes(lambda n: isinstance(n, ast.Name), node)
    return cast("list[ast.Name]", found)


def return_nodes_in_ast(node: Any) -> list[ast.Return]:
    """Returns all `Return` nodes occurring in an AST."""
    found = find_nodes(lambda n: isinstance(n, ast.Return), node, {ast.FunctionDef})
    return cast("list[ast.Return]", found)


def loop_in_ast(node: Any) -> list[ast.For | ast.While]:
    """Returns all `For` and `While` nodes occurring in an AST."""
    found = find_nodes(
        lambda n: isinstance(n, ast.For | ast.While), node, {ast.FunctionDef}
    )
    return cast("list[ast.For | ast.While]", found)


def breaks_in_loop(node: Any) -> list[ast.Break]:
    """Returns all `Break` nodes occurring in a loop.

    Note that breaks in nested loops are excluded.
    """
    found = find_nodes(
        lambda n: isinstance(n, ast.Break), node, {ast.For, ast.While, ast.FunctionDef}
    )
    return cast("list[ast.Break]", found)


def loop_controls_in_loop(node: Any) -> list[ast.Break | ast.Continue]:
    """Returns all `Break` and `Continue` nodes occurring in a loop.

    Note that breaks in nested loops are excluded.
    """
    found = find_nodes(
        lambda n: isinstance(n, ast.Break | ast.Continue),
        node,
        {ast.For, ast.While, ast.FunctionDef},
    )
    return cast("list[ast.Break | ast.Continue]", found)


class ContextAdjuster(ast.NodeTransformer):
    """Updates the `ast.Context` indicating if expressions occur on the LHS or RHS."""

    ctx: ast.expr_context

    def __init__(self, ctx: ast.expr_context) -> None:
        self.ctx = ctx

    def visit(self, node: ast.AST) -> ast.AST:
        return cast("ast.AST", super().visit(node))

    def visit_Name(self, node: ast.Name) -> ast.Name:
        return with_loc(node, ast.Name(id=node.id, ctx=self.ctx))

    def visit_Starred(
        self,
        node: ast.Starred,
    ) -> ast.Starred:
        return with_loc(
            node,
            ast.Starred(value=self.visit(node.value), ctx=self.ctx),  # type: ignore[arg-type]
        )

    def visit_Tuple(self, node: ast.Tuple) -> ast.Tuple:
        return with_loc(
            node,
            ast.Tuple(
                elts=[self.visit(elt) for elt in node.elts],  # type: ignore[misc]
                ctx=self.ctx,
            ),
        )

    def visit_List(self, node: ast.List) -> ast.List:
        return with_loc(
            node,
            ast.List(
                elts=[self.visit(elt) for elt in node.elts],  # type: ignore[misc]
                ctx=self.ctx,
            ),
        )

    def visit_Subscript(self, node: ast.Subscript) -> ast.Subscript:
        # Don't adjust the slice!
        return with_loc(
            node,
            ast.Subscript(
                value=self.visit(node.value),  # type: ignore[arg-type]
                slice=node.slice,
                ctx=self.ctx,
            ),
        )

    def visit_Attribute(self, node: ast.Attribute) -> ast.Attribute:
        return with_loc(
            node,
            ast.Attribute(
                value=self.visit(node.value),  # type: ignore[arg-type]
                attr=node.attr,
                ctx=self.ctx,
            ),
        )


@dataclass(frozen=True, eq=False)
class TemplateReplacer(ast.NodeTransformer):
    """Replaces nodes in a template."""

    replacements: Mapping[str, ast.AST | Sequence[ast.AST]]
    default_loc: ast.AST

    def _get_replacement(self, x: str) -> ast.AST | Sequence[ast.AST]:
        if x not in self.replacements:
            msg = f"No replacement for `{x}` is given"
            raise ValueError(msg)
        return self.replacements[x]

    def visit_Name(self, node: ast.Name) -> ast.AST:
        repl = self._get_replacement(node.id)
        if not isinstance(repl, ast.expr):
            msg = f"Replacement for `{node.id}` must be an expression"
            raise TypeError(msg)

        # Update the context
        adjuster = ContextAdjuster(node.ctx)
        return with_loc(repl, adjuster.visit(repl))

    def visit_Expr(self, node: ast.Expr) -> ast.AST | Sequence[ast.AST]:
        if isinstance(node.value, ast.Name):
            repl = self._get_replacement(node.value.id)
            repls = [repl] if not isinstance(repl, Sequence) else repl
            # Wrap expressions to turn them into statements
            return [
                with_loc(r, ast.Expr(value=r)) if isinstance(r, ast.expr) else r
                for r in repls
            ]
        return self.generic_visit(node)

    def generic_visit(self, node: ast.AST) -> ast.AST:
        # Insert the default location
        node = super().generic_visit(node)
        return with_loc(self.default_loc, node)


def template_replace(
    template: str, default_loc: ast.AST, **kwargs: ast.AST | Sequence[ast.AST]
) -> list[ast.stmt]:
    """Turns a template into a proper AST by substituting all placeholders."""
    nodes = ast.parse(textwrap.dedent(template)).body
    replacer = TemplateReplacer(kwargs, default_loc)
    new_nodes = []
    for n in nodes:
        new = replacer.visit(n)
        if isinstance(new, list):
            new_nodes.extend(new)
        else:
            new_nodes.append(new)
    return new_nodes


def line_col(node: ast.AST) -> tuple[int, int]:
    """Returns the line and column of an ast node."""
    return node.lineno, node.col_offset  # type: ignore[attr-defined]


def set_location_from(node: ast.AST, loc: ast.AST) -> None:
    """Copy source location from one AST node to the other."""
    node.lineno = loc.lineno  # type: ignore[attr-defined]
    node.col_offset = loc.col_offset  # type: ignore[attr-defined]
    node.end_lineno = loc.end_lineno  # type: ignore[attr-defined]
    node.end_col_offset = loc.end_col_offset  # type: ignore[attr-defined]

    source, file, line_offset = get_source(loc), get_file(loc), get_line_offset(loc)
    assert source is not None
    assert file is not None
    assert line_offset is not None
    annotate_location(node, source, file, line_offset)


def annotate_location(
    node: ast.AST,
    source: str,
    file: str,
    line_offset: int,
    recurse: bool = True,
) -> None:
    node.line_offset = line_offset  # type: ignore[attr-defined]
    node.file = file  # type: ignore[attr-defined]
    node.source = source  # type: ignore[attr-defined]

    if recurse:
        for _field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        annotate_location(item, source, file, line_offset, recurse)
            elif isinstance(value, ast.AST):
                annotate_location(value, source, file, line_offset, recurse)


def shift_loc(node: ast.AST, delta_lineno: int, delta_col_offset: int) -> None:
    """Shifts all line and column number in the AST node by the given amount."""
    if hasattr(node, "lineno"):
        node.lineno += delta_lineno
    if hasattr(node, "end_lineno") and node.end_lineno is not None:
        node.end_lineno += delta_lineno
    if hasattr(node, "col_offset"):
        node.col_offset += delta_col_offset
    if hasattr(node, "end_col_offset") and node.end_col_offset is not None:
        node.end_col_offset += delta_col_offset
    for _, value in ast.iter_fields(node):
        if isinstance(value, list):
            for item in value:
                if isinstance(item, ast.AST):
                    shift_loc(item, delta_lineno, delta_col_offset)
        elif isinstance(value, ast.AST):
            shift_loc(value, delta_lineno, delta_col_offset)


def get_file(node: AstNode) -> str | None:
    """Tries to retrieve a file annotation from an AST node."""
    try:
        file = node.file  # type: ignore[union-attr]
        return file if isinstance(file, str) else None
    except AttributeError:
        return None


def get_source(node: AstNode) -> str | None:
    """Tries to retrieve a source annotation from an AST node."""
    try:
        source = node.source  # type: ignore[union-attr]
        return source if isinstance(source, str) else None
    except AttributeError:
        return None


def get_line_offset(node: AstNode) -> int | None:
    """Tries to retrieve a line offset annotation from an AST node."""
    try:
        line_offset = node.line_offset  # type: ignore[union-attr]
        return line_offset if isinstance(line_offset, int) else None
    except AttributeError:
        return None


A = TypeVar("A", bound=ast.AST)


def with_loc(loc: ast.AST, node: A) -> A:
    """Copy source location from one AST node to the other."""
    set_location_from(node, loc)
    return node


def with_type(ty: "Type", node: A) -> A:
    """Annotates an AST node with a type."""
    node.type = ty  # type: ignore[attr-defined]
    return node


def get_type_opt(node: AstNode) -> Optional["Type"]:
    """Tries to retrieve a type annotation from an AST node."""
    from guppylang_internals.tys.ty import TypeBase

    try:
        ty = node.type  # type: ignore[union-attr]
        return cast("Type", ty) if isinstance(ty, TypeBase) else None
    except AttributeError:
        return None


def get_type(node: AstNode) -> "Type":
    """Retrieve a type annotation from an AST node.

    Fails if the node is not annotated.
    """
    ty = get_type_opt(node)
    assert ty is not None
    return ty


def has_empty_body(func_ast: ast.FunctionDef) -> bool:
    """Returns `True` if the body of a function definition is empty.

    This is the case if the body only contains a single `pass` statement or an ellipsis
    `...` expression.
    """
    if len(func_ast.body) == 0:
        return True
    if len(func_ast.body) > 1:
        return False
    [n] = func_ast.body
    return (
        isinstance(n, ast.Expr)
        and isinstance(n.value, ast.Constant)
        and n.value.value == Ellipsis
    )
