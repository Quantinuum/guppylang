"""Reference to the extension currently being built or used by decorated ops."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hugr.ext import Extension


@dataclass
class ExtensionState:
    extension: Extension | None = None


EXTENSION_STATE = ExtensionState()
