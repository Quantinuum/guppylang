import ast
from dataclasses import dataclass, field

from hugr.debug_info import DILocation

from guppylang_internals.ast_util import AstNode, get_file
from guppylang_internals.debug_mode import debug_mode_enabled
from guppylang_internals.span import to_span


def debug_conditions_fulfilled(ast_node: AstNode | None) -> bool:
    """Checks whether the conditions for debug information attachment are fulfilled,
    i.e. whether we're in debug mode and we have a current AST node with an attached
    file."""
    return (
        debug_mode_enabled() and ast_node is not None and get_file(ast_node) is not None
    )


def make_location_record(node: ast.AST) -> DILocation:
    """Creates a DILocation metadata record for `node`."""
    return DILocation(
        line_no=to_span(node).start.line, column=to_span(node).start.column
    )


@dataclass
class StringTable:
    """Utility class for managing a string table for debug info serialization."""

    table: list[str] = field(default_factory=list)

    def get_index(self, s: str) -> int:
        """Returns the index of `s` in the string table, adding it if it's not already
        present."""
        try:
            return self.table.index(s)
        except ValueError:
            idx = len(self.table)
            self.table.append(s)
            return idx

    def get_string(self, idx: int) -> str:
        """Returns the string corresponding to `idx` in the string table."""
        return self.table[idx]
