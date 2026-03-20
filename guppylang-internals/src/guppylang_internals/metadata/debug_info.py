import ast
from dataclasses import dataclass

from hugr.debug_info import DILocation

from guppylang_internals.span import to_span


def make_location_record(node: ast.AST) -> DILocation:
    """Creates a DILocation metadata record for `node`."""
    return DILocation(
        line_no=to_span(node).start.line, column=to_span(node).start.column
    )


@dataclass
class StringTable:
    """Utility class for managing a string table for debug info serialization."""

    table: list[str]

    def get_index(self, s: str) -> int:
        """Returns the index of `s` in the string table, adding it if it's not already
        present."""
        for idx, entry in enumerate(self.table):
            if entry == s:
                return idx
        else:
            idx = len(self.table)
            self.table.append(s)
            return idx

    def get_string(self, idx: int) -> str:
        """Returns the string corresponding to `idx` in the string table."""
        return self.table[idx]
