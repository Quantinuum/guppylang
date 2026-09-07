"""Make the release scripts importable from the tests.

The scripts under ``scripts/release`` are standalone (no package), so we add that
directory to ``sys.path`` here, allowing the tests to ``import compute_versions``
and ``import extract_changelog`` directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "release"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
