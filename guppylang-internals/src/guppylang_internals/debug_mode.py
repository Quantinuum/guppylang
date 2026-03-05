"""Global state for determining whether to attach debug information to Hugr nodes
during compilation."""

DEBUG_MODE_ENABLED = False


def turn_on_debug_mode() -> None:
    global DEBUG_MODE_ENABLED
    DEBUG_MODE_ENABLED = True


def turn_off_debug_mode() -> None:
    global DEBUG_MODE_ENABLED
    DEBUG_MODE_ENABLED = False


def debug_mode_enabled() -> bool:
    return DEBUG_MODE_ENABLED
