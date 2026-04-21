"""TODO: NICOLa add docstring"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any

from guppylang_internals.ast_util import get_type
from guppylang_internals.checker.errors.generic import (
    NonExhaustiveMatchError,
)
from guppylang_internals.error import (
    GuppyError,
    InternalGuppyError,
)
from guppylang_internals.nodes import (
    CheckedMatchPred,
    MatchEnum,
    MatchLiteral,
    MatchOverLiteral,
    MatchStruct,
)
from guppylang_internals.tys.ty import EnumType, OpaqueType, StructType

# A matrix of patterns, where each row corresponds to a case in the match case statement
Matrix = list[list[ast.pattern]]
# A mapping from Matrix row index to the index of the case in the match statement.
Actions = list[int]
# An occurrence identifies a subterm path (1-indexed at each level).
# e.g. (1,) is the 1st top-level value; (1, 2) is the 2nd arg of the 1st value.
Occurrence = tuple[int, ...]


# ---------------------------------------------------------------------------
# Decision Trees
# ---------------------------------------------------------------------------


@dataclass
class Leaf:
    action: int

    def __repr__(self) -> str:
        return f"Leaf({self.action})"


@dataclass
class Switch:
    occurrence: Occurrence
    # Each case is (constructor_name_or_None, subtree).
    # None means the wildcard/default case.
    cases: list[tuple[ast.pattern | None, DecisionTree]]

    def __repr__(self) -> str:
        case_strs = []
        for key, tree in self.cases:
            label = key if key is not None else "_"
            case_strs.append(f"{label}: {tree!r}")
        return f"Switch({self.occurrence}, [{', '.join(case_strs)}])"


def pretty(tree: DecisionTree, indent: int = 0) -> str:
    pad = "  " * indent
    if isinstance(tree, Leaf):
        return f"{pad}Leaf({tree.action})"
    if isinstance(tree, Switch):
        occ_str = ".".join(str(x) for x in tree.occurrence)
        lines = [f"{pad}Switch({occ_str},"]
        for key, subtree in tree.cases:
            label = key if key is not None else "_"
            lines.append(f"{pad}  {label}=>")
            lines.append(pretty(subtree, indent + 2))
        lines.append(f"{pad})")
        return "\n".join(lines)
    raise TypeError(f"Unknown tree node: {type(tree)}")


DecisionTree = Leaf | Switch


def arity(c: ast.pattern) -> int:
    match c:
        case MatchStruct():
            struct_ty = get_type(c.struct)
            assert isinstance(struct_ty, StructType)
            return len(struct_ty.fields)
        case MatchEnum():
            enum_ty = get_type(c.enum)
            assert isinstance(enum_ty, EnumType)
            return len(enum_ty.variants_as_list[c.variant_idx].fields)
        case MatchLiteral():
            return 0
        case _:
            raise InternalGuppyError(f"Unexpected pattern {c}")


def specialize(
    c: ast.pattern, col_idx: int, matrix: Matrix, actions: Actions
) -> tuple[Matrix, Actions]:
    """TODO: S(c, P→A): keep rows compatible with constructor c at column col_idx,
    expanding its arguments in place of that pattern."""
    new_matrix: Matrix = []
    new_actions: Actions = []
    for row, action in zip(matrix, actions, strict=True):
        patt = row[col_idx]
        before, after = list(row[:col_idx]), list(row[col_idx + 1 :])
        a = arity(c)
        match patt:
            case MatchLiteral(constant=ast.Constant(value=value)):
                assert isinstance(c, MatchLiteral)
                if c.constant.value == value:
                    new_matrix.append(before + after)
                    new_actions.append(action)
            case ast.MatchAs():
                # We add wildcards to the line to preserve the number of columns
                new_matrix.append(before + [ast.MatchAs()] * a + after)
                new_actions.append(action)
            case MatchStruct():
                args = patt.patterns
                assert len(args) == a
                new_matrix.append(before + args + after)
                new_actions.append(action)
            case MatchEnum(variant_idx=variant_idx, patterns=args):
                assert isinstance(c, MatchEnum)
                if c.variant_idx == variant_idx:
                    assert len(args) == a
                    new_matrix.append(before + args + after)
                    new_actions.append(action)
            case _:
                raise InternalGuppyError(f"Unexpected pattern {c}")
            # constructor with different name: row is dropped
    return new_matrix, new_actions


def default_matrix(
    col_idx: int, matrix: Matrix, actions: Actions
) -> tuple[Matrix, Actions]:
    """D(P→A): keep only rows whose pattern at col_idx is a wildcard,
    dropping that column."""
    new_matrix: Matrix = []
    new_actions: Actions = []
    for row, action in zip(matrix, actions, strict=True):
        if isinstance(row[col_idx], ast.MatchAs):
            new_matrix.append(list(row[:col_idx]) + list(row[col_idx + 1 :]))
            new_actions.append(action)
    return new_matrix, new_actions


def build_decision_tree(
    occurrences: list[Occurrence],
    pattern_matrix: Matrix,
    actions: Actions,
    main_node: ast.expr,
) -> DecisionTree:
    """Builds a decision tree from the given matrix and actions. The decision tree is
    represented as an ast.expr, where the leaves are the actions and the internal nodes
    are the pattern matching expressions."""

    # Case 1 - If the pattern matrix is empty, then we have a non exhaustive match
    # because we have no patterns to match against but we are still inspecting
    if len(pattern_matrix) == 0:
        raise GuppyError(NonExhaustiveMatchError(main_node))

    num_cols = len(pattern_matrix[0])
    # Case 2 — first row is all wildcards (matches unconditionally)
    if num_cols == 0 or all(isinstance(p, ast.MatchAs) for p in pattern_matrix[0]):
        # TODO: If there are multiple rows, we can raise a warning about unreachable
        # patterns (maybe we can have a better way to report the warning)
        return Leaf(actions[0])

    # We find the first column of that contains a non wildcard pattern (at any row)
    # TODO: (here we will introduce heuristics in the future)
    col_idx: int | None = None
    founded_pattern: ast.pattern | None = None
    for j in range(num_cols):
        for row in pattern_matrix:
            if not isinstance(row[j], ast.MatchAs):
                col_idx = j
                founded_pattern = row[j]
                break

    # We know there is at least one non wildcard in first row
    assert col_idx is not None
    assert founded_pattern is not None

    chosen_occ = occurrences[col_idx]
    other_occs = list(occurrences[:col_idx]) + list(occurrences[col_idx + 1 :])

    # Used to keep track of the constructors we have already seen in the column
    sigma: set[Any] = set()
    # Check if the matching is exhaustive (only for enums) TODO: NICOLA, improve this,
    # we should check also for Literals
    constructor_count = 0
    is_complete_signature = False

    # TODO: NICOLA, Refactor this, very ugly
    cases: list[tuple[ast.pattern | None, DecisionTree]] = []
    for row in pattern_matrix:
        c = row[col_idx]
        # This match is based on the hypothesis that all the patterns in the same column
        # have the same type
        # TODO: NICOLA Refactor the nodes to avoid this ugly match (e.g. define a common
        # base class with abstract id method)
        match c:
            case MatchLiteral(constant=ast.Constant(value=value)):
                if value in sigma:
                    continue
                lit_ty = get_type(c)
                if isinstance(lit_ty, OpaqueType) and lit_ty.defn.name == "bool":
                    constructor_count += 1
                    if constructor_count == 2:
                        is_complete_signature = True
                sigma.add(value)
            case MatchStruct(struct=struct):
                if struct.id in sigma:
                    continue
                sigma.add(struct.id)
            case MatchEnum(variant_idx=variant_idx):
                if variant_idx in sigma:
                    continue
                constructor_count += 1
                enum_ty = get_type(c.enum)
                assert isinstance(enum_ty, EnumType)
                if constructor_count == len(enum_ty.variants_as_list):
                    is_complete_signature = True
                sigma.add(variant_idx)
            case ast.MatchAs():
                continue
            case _:
                raise InternalGuppyError(f"Unexpected pattern {c}")

        a = arity(c)
        updated_occurrences = (
            list(occurrences[:col_idx])
            + [(*chosen_occ, k) for k in range(a)]
            + list(occurrences[col_idx + 1 :])
        )
        specialized_matrix, specialized_actions = specialize(
            c, col_idx, pattern_matrix, actions
        )
        if isinstance(c, MatchStruct):
            # We only need to unpack the struct arguments
            return build_decision_tree(
                updated_occurrences,
                specialized_matrix,
                specialized_actions,
                main_node,
            )

        cases.append(
            (
                c,
                build_decision_tree(
                    updated_occurrences,
                    specialized_matrix,
                    specialized_actions,
                    main_node,
                ),
            )
        )
    if not is_complete_signature:
        pattern_defaults, action_defaults = default_matrix(
            col_idx,
            pattern_matrix,
            actions,
        )
        cases.append(
            (
                None,
                build_decision_tree(
                    other_occs,
                    pattern_defaults,
                    action_defaults,
                    main_node,
                ),
            )
        )

    return Switch(chosen_occ, cases)


# ---------------------------------------------------------------------------
# DAG compaction (maximally shared DAG)
# ---------------------------------------------------------------------------

# A unique table maps a structural key to the canonical DAG node.
# Python object identity (id()) of canonical nodes serves as their unique ID.
_UniqueTable = dict[Any, DecisionTree]


def _case_label_key(label: ast.pattern | None) -> Any:
    """Returns a hashable structural key for a Switch case label."""
    if label is None:
        return None
    if isinstance(label, MatchLiteral):
        return ("lit", label.constant.value)
    if isinstance(label, MatchEnum):
        return ("enum", label.variant_idx)
    if isinstance(label, MatchStruct):
        return ("struct", label.struct.id)
    raise InternalGuppyError(f"Unexpected case label pattern: {label}")


def tree_to_dag(
    node: DecisionTree,
    unique_table: _UniqueTable | None = None,
) -> DecisionTree:
    """Transforms a decision tree into a maximally shared DAG.

    Uses a bottom-up structural hashing pass to merge identical subtrees into a
    single shared node, and eliminates redundant Switch nodes whose every branch
    leads to the same child.

    Steps:
      1. Leaf merging  — all leaves with the same action map to one canonical node.
      2. Bottom-up recursion — children are reduced before their parent.
      3. Redundancy elimination — a Switch node is removed when every branch points
         to the same already-reduced child.
      4. Structural hashing — an existing node is reused whenever the (occurrence,
         per-case label, child-identity) key is already present in the table.

    Args:
        node: Root of the decision tree to compact.
        unique_table: Shared hash table mapping structural keys to canonical nodes.
                      Pass an empty dict to start fresh, or omit to create one
                      automatically (single-tree compaction).

    Returns:
        Root of the maximally shared DAG.
    """
    if unique_table is None:
        unique_table = {}

    # Step 1: Leaf merging — all leaves with the same action share one node.
    if isinstance(node, Leaf):
        key: Any = ("leaf", node.action)
        if key not in unique_table:
            unique_table[key] = node
        return unique_table[key]

    # Step 2: Bottom-up recursion — reduce each child before this node.
    reduced_cases: list[tuple[ast.pattern | None, DecisionTree]] = [
        (label, tree_to_dag(child, unique_table)) for label, child in node.cases
    ]

    # Step 3: Redundancy elimination — drop this Switch when all branches agree.
    child_nodes = [child for _, child in reduced_cases]
    if child_nodes and all(child is child_nodes[0] for child in child_nodes[1:]):
        return child_nodes[0]

    # Step 4: Structural hashing — reuse an existing node if structurally identical.
    # The key encodes the occurrence + per-case (label, child identity).
    cases_key = tuple(
        (_case_label_key(label), id(child)) for label, child in reduced_cases
    )
    key = ("switch", node.occurrence, cases_key)

    if key not in unique_table:
        unique_table[key] = Switch(occurrence=node.occurrence, cases=reduced_cases)

    return unique_table[key]


def pretty_dag(root: DecisionTree) -> str:
    """Returns a human-readable textual representation of a maximally shared DAG.

    Unlike ``pretty()``, which traverses the tree recursively and may print the same
    subtree multiple times, this function assigns a stable short identifier (``n0``,
    ``n1``, …) to every unique node (detected via Python object identity), visits each
    node exactly once with BFS, and uses ``->nN`` back-references when a child has
    already been printed.

    Example output::

        n0: Leaf(0)
        n1: Leaf(1)
        n2: Switch(0)
              True  -> n0
              False -> n1
        root -> n2
    """
    # BFS to collect all unique nodes in visitation order.
    node_id: dict[int, int] = {}  # id(node) -> short integer label
    ordered: list[DecisionTree] = []
    queue: list[DecisionTree] = [root]
    while queue:
        current = queue.pop(0)
        key = id(current)
        if key in node_id:
            continue
        node_id[key] = len(node_id)
        ordered.append(current)
        if isinstance(current, Switch):
            for _, child in current.cases:
                if id(child) not in node_id:
                    queue.append(child)

    lines: list[str] = []
    for node in ordered:
        nid = f"n{node_id[id(node)]}"
        if isinstance(node, Leaf):
            lines.append(f"{nid}: Leaf({node.action})")
        else:
            occ_str = ".".join(str(x) for x in node.occurrence)
            lines.append(f"{nid}: Switch({occ_str})")
            for label, child in node.cases:
                label_str = _case_label_key(label)
                child_ref = f"n{node_id[id(child)]}"
                lines.append(f"      {label_str!s:<12} -> {child_ref}")

    root_ref = f"n{node_id[id(root)]}"
    lines.append(f"root -> {root_ref}")
    return "\n".join(lines)


def post_process_match_pred(node: CheckedMatchPred) -> ast.expr:
    """After the checking we need to pre-compile the decision tree for the pattern
    match statement. We compute it in the checking since it allows us to check
    exhaustiveness too"""
    # TODO: Testing
    match node:
        case MatchOverLiteral(subj_type=OpaqueType(defn=defn)) if defn.name == "bool":
            literal_values: set[bool] = set()
            for p in node.patterns:
                if isinstance(p, ast.MatchAs):
                    # We have a wildcard pattern, thus the match is exhaustive
                    return node
                assert isinstance(p, MatchLiteral)
                assert isinstance(p.constant.value, bool)
                literal_values.add(p.constant.value)

            missing_values = {True, False} - literal_values
            if len(missing_values) == 0:
                return node
        case MatchOverLiteral():
            if isinstance(node.patterns[-1], ast.MatchAs):
                # We are matching on a literal, thus there are infinite possible
                # patterns and the last pattern needs to be a wildcard
                # No other pre compilation is needed for the decision tree
                return node
        case _:
            # TODO: NICOLa update when we add different patterns (such as tuple)
            pattern_matrix: Matrix = [[p] for p in node.patterns]
            tree = build_decision_tree(
                [(0,)],
                pattern_matrix,
                list(range(len(node.patterns))),
                node,
            )
            print("Before DAG compaction:")
            print(pretty(tree=tree))
            _dag = tree_to_dag(tree)
            print("After DAG compaction:")
            print(pretty_dag(_dag))
            return node

    raise GuppyError(NonExhaustiveMatchError(node))
