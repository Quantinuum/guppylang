from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from types import CodeType, FrameType, TracebackType


@dataclass(frozen=True)
class FrameSnapshot:
    """Definition scope and source information without retaining caller frames.

    Using a FrameSnapshot rather than a FrameType helps avoid retaining the
    entire call stack in memory.
    """

    f_locals: dict[str, Any]
    f_globals: dict[str, Any]
    f_builtins: dict[str, Any]
    f_code: CodeType
    f_back: None = None

    @classmethod
    def from_frame(cls, frame: FrameType) -> FrameSnapshot:
        """Copy locals after checking, when forward definitions are available."""
        # On Python 3.13+, f_locals is a proxy that itself retains the frame.
        # Module namespaces are already ordinary dictionaries and must stay live.
        locals = (
            frame.f_globals
            if frame.f_locals is frame.f_globals
            else dict(frame.f_locals)
        )
        return cls(locals, frame.f_globals, frame.f_builtins, frame.f_code)


def get_calling_frame(*, skip_main_lang: bool = True) -> FrameType:
    """Finds the first frame that called this function that either has an unknown
    module, or the module is outside the compiler packages.

    :param skip_main_lang: Whether to skip frames that belong to modules in the main
        guppylang language package. Set to False if you want to resolve calling frames
        in e.g. the std lib.
    """
    frame = inspect.currentframe()
    while frame:
        module_name = frame.f_globals.get("__name__")
        if module_name is None:
            return frame
        elif _is_main_lang_module(module_name):
            if not skip_main_lang:
                return frame
        elif _is_internals_module(module_name):
            pass
        else:
            return frame

        frame = frame.f_back

    raise RuntimeError("Could not obtain stack frame for definition")


def remove_internal_frames(tb: TracebackType | None) -> TracebackType | None:
    """Removes internal frames from compiler modules from a traceback."""
    if tb:
        module = inspect.getmodule(tb.tb_frame)
        if module is not None and (
            _is_main_lang_module(module.__name__)
            or _is_internals_module(module.__name__)
        ):
            return remove_internal_frames(tb.tb_next)
        if tb.tb_next:
            tb.tb_next = remove_internal_frames(tb.tb_next)
    return tb


def _is_main_lang_module(module_name: str) -> bool:
    return module_name.startswith("guppylang.")


def _is_internals_module(module_name: str) -> bool:
    return module_name.startswith("guppylang_internals.")
