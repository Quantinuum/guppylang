from guppylang_internals.experimental import enable_experimental_features
from guppylang_internals.warning import GuppyWarning, rich_warnings

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std import builtins, debug, quantum
from guppylang.std.builtins import array, comptime, py
from guppylang.std.quantum import qubit

__all__ = (
    "GuppyModule",
    "GuppyWarning",
    "array",
    "builtins",
    "comptime",
    "debug",
    "enable_experimental_features",
    "guppy",
    "py",
    "quantum",
    "qubit",
    "rich_warnings",
)

# This is kept in sync with the project version by the release workflow
# (.github/workflows/release-pr.yml).
__version__ = "1.0.0-a6"
