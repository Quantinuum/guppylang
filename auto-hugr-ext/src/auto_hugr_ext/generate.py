"""Entry point for generating a new HUGR extension from a source file."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from guppylang_internals.engine import ENGINE

from auto_hugr_ext.extension import build_extension
from auto_hugr_ext.harvest import harvest
from auto_hugr_ext.state import EXTENSION_STATE

if TYPE_CHECKING:
    from hugr.ext import Extension

__all__ = ["generate_new_hugr_ext", "register_extension"]


def generate_new_hugr_ext(
    source_path: str | Path, ext_name: str, out_path: str | Path | None = None
) -> Extension:
    """Builds and returns a HUGR Extension from declarations in `source_path`.

    The extension's standard HUGR JSON representation is written to `out_path`,
    defaulting to `<source stem>.json` next to the source file.
    """
    source_path = Path(source_path)
    if out_path is None:
        out_path = source_path.with_suffix(".json")
    EXTENSION_STATE.extension = None
    extension = build_extension(ext_name, harvest(source_path))
    Path(out_path).write_text(extension.to_json(), encoding="utf-8")
    return extension


def register_extension(extension: Extension) -> None:
    """Register an extension with Guppy's global compilation engine."""
    if not any(
        registered.name == extension.name and registered.version == extension.version
        for registered in ENGINE.additional_extensions
    ):
        ENGINE.additional_extensions.append(extension)
