from guppylang_internals.experimental import enable_experimental_features

from guppylang.decorator import Effect, guppy
from guppylang.module import GuppyModule
from guppylang.std import builtins, debug, quantum
from guppylang.std.builtins import array, comptime, py
from guppylang.std.quantum import qubit

__all__ = (
    "Effect",
    "GuppyModule",
    "array",
    "builtins",
    "comptime",
    "debug",
    "enable_experimental_features",
    "guppy",
    "py",
    "quantum",
    "qubit",
)

# This is updated by our release-please workflow, triggered by this
# annotation: x-release-please-version
__version__ = "1.0.0-a5"
