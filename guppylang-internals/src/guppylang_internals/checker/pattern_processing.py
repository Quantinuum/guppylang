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
            print(pretty(tree=tree))
            return node

    raise GuppyError(NonExhaustiveMatchError(node))
