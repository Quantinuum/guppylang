from ast import expr
from dataclasses import dataclass
from typing import ClassVar

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.errors.generic import UnsupportedError
from guppylang_internals.diagnostic import Error, Help
from guppylang_internals.error import GuppyError

EXPERIMENTAL_FEATURES_ENABLED = False


def are_experimental_features_enabled() -> bool:
    """Whether experimental Guppy features are enabled."""
    return EXPERIMENTAL_FEATURES_ENABLED


def enable_experimental_features() -> None:
    """Enables experimental Guppy features."""
    set_experimental_features_enabled(True)


def disable_experimental_features() -> None:
    """Disables experimental Guppy features."""
    set_experimental_features_enabled(False)


def set_experimental_features_enabled(enabled: bool) -> None:
    """Sets whether experimental Guppy features are enabled."""
    global EXPERIMENTAL_FEATURES_ENABLED
    EXPERIMENTAL_FEATURES_ENABLED = enabled


@dataclass(frozen=True)
class ExperimentalFeatureError(Error):
    title: ClassVar[str] = "Experimental feature"
    span_label: ClassVar[str] = "{things} are an experimental feature"
    things: str

    @dataclass(frozen=True)
    class Suggestion(Help):
        message: ClassVar[str] = (
            "Experimental features are currently disabled. You can enable them by "
            "calling `guppylang.enable_experimental_features()`, however note that "
            "these features are unstable and might break in the future."
        )

    def __post_init__(self) -> None:
        self.add_sub_diagnostic(ExperimentalFeatureError.Suggestion(None))


def check_function_tensors_enabled(node: expr | None = None) -> None:
    if not EXPERIMENTAL_FEATURES_ENABLED:
        raise GuppyError(ExperimentalFeatureError(node, "Function tensors"))


def check_lists_enabled(loc: AstNode | None = None) -> None:
    if not EXPERIMENTAL_FEATURES_ENABLED:
        raise GuppyError(ExperimentalFeatureError(loc, "Lists"))


def check_capturing_closures_enabled(loc: AstNode | None = None) -> None:
    if not EXPERIMENTAL_FEATURES_ENABLED:
        raise GuppyError(UnsupportedError(loc, "Capturing closures"))


def check_modifiers_enabled(loc: AstNode | None = None) -> None:
    if not EXPERIMENTAL_FEATURES_ENABLED:
        raise GuppyError(ExperimentalFeatureError(loc, "Modifiers"))
