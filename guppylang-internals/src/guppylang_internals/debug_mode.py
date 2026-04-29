"""Global state for determining whether to attach debug information to Hugr nodes
during compilation."""

import os

_DEBUG_MODE_ENABLED = os.getenv("GUPPYLANG_FORCE_DEBUGINFO") == "1"


def turn_on_debug_mode() -> None:
    global _DEBUG_MODE_ENABLED
    _DEBUG_MODE_ENABLED = True


def turn_off_debug_mode() -> None:
    global _DEBUG_MODE_ENABLED
    _DEBUG_MODE_ENABLED = False


def debug_mode_enabled() -> bool:
    return _DEBUG_MODE_ENABLED
