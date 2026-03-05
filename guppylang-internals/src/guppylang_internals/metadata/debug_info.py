import ast
from abc import ABC, abstractmethod
from dataclasses import dataclass

from hugr.metadata import JsonType, Metadata

from guppylang_internals.span import to_span


@dataclass
class DebugRecord(ABC):
    """Abstract base class for debug records."""

    @abstractmethod
    def to_json(self) -> JsonType:
        """Encodes the record as a dictionary of native types that can be serialized by
        `json.dump`.
        """

    @classmethod
    @abstractmethod
    def from_json(cls, value: JsonType) -> "DebugRecord":
        """Decodes the extension from a native types obtained from `json.load`."""


class HugrDebugInfo(Metadata[DebugRecord]):
    """Metadata storing debug information for a node."""

    KEY = "core.debug_info"

    @classmethod
    def to_json(cls, value: DebugRecord) -> JsonType:
        return value.to_json()

    @classmethod
    def from_json(cls, value: JsonType) -> DebugRecord:
        return DebugRecord.from_json(value)


@dataclass
class DICompileUnit(DebugRecord):
    """Debug information for a compilation unit, corresponds to a module node."""

    directory: str
    filename: int  # File that contains Hugr entrypoint.
    file_table: list[str]  # Global table of all files referenced in the module.

    def to_json(self) -> dict[str, JsonType]:
        return {
            "directory": self.directory,
            "filename": self.filename,
            # TODO: Fix table conversion / typing.
            "file_table": self.file_table,
        }

    @classmethod
    def from_json(cls, value: JsonType) -> "DICompileUnit":
        if not isinstance(value, dict):
            msg = f"Expected a dictionary for DICompileUnit, but got {type(value)}"
            raise TypeError(msg)
        for key in ("directory", "filename", "file_table"):
            if key not in value:
                msg = f"Expected DICompileUnit to have a '{key}' key but got {value}"
                raise TypeError(msg)
        files = value["file_table"]
        if not isinstance(files, list):
            msg = f"Expected 'file_table' to be a list but got {type(files)}"
            raise TypeError(msg)
        return DICompileUnit(
            directory=str(value["directory"]),
            filename=int(value["filename"]),
            file_table=list[str](value["file_table"]),
        )


@dataclass
class DISubprogram(DebugRecord):
    """Debug information for a subprogram, corresponds to a function definition or
    declaration node."""

    file: int  # Index into the string table for filenames.
    line_no: int  # First line of the function definition.
    scope_line: int | None = None  # First line of the function body.

    def to_json(self) -> dict[str, str]:
        return (
            {
                "file": str(self.file),
                "line_no": str(self.line_no),
                "scope_line": str(self.scope_line),
            }
            # Declarations have no function body so could have no scope_line.
            if self.scope_line is not None
            else {
                "file": str(self.file),
                "line_no": str(self.line_no),
            }
        )

    @classmethod
    def from_json(cls, value: JsonType) -> "DISubprogram":
        if not isinstance(value, dict):
            msg = f"Expected a dictionary for DISubprogram, but got {type(value)}"
            raise TypeError(msg)
        for key in ("file", "line_no"):
            if key not in value:
                msg = f"Expected DISubprogram to have a '{key}' key but got {value}"
                raise TypeError(msg)
        # Declarations have no function body so could have no scope_line.
        scope_line = int(value["scope_line"]) if "scope_line" in value else None
        return DISubprogram(
            file=int(value["file"]),
            line_no=int(value["line_no"]),
            scope_line=scope_line,
        )


@dataclass
class DILocation(DebugRecord):
    """Debug information for a location, corresponds to call or extension operation
    node."""

    column: int
    line_no: int

    def to_json(self) -> dict[str, str]:
        return {
            "column": str(self.column),
            "line_no": str(self.line_no),
        }

    @classmethod
    def from_json(cls, value: JsonType) -> "DILocation":
        if not isinstance(value, dict):
            msg = f"Expected a dictionary for DILocation, but got {type(value)}"
            raise TypeError(msg)
        for key in ("column", "line_no"):
            if key not in value:
                msg = f"Expected DILocation to have a '{key}' key but got {value}"
                raise TypeError(msg)
        return DILocation(column=int(value["column"]), line_no=int(value["line_no"]))


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
