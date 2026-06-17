import inspect
from types import FrameType, ModuleType, TracebackType


def get_calling_frame(*, skip_main_lang: bool = True) -> FrameType:
    """Finds the first frame that called this function that either has an unknown
    module, or the module is outside the compiler packages.

    :param skip_main_lang: Whether to skip frames that belong to modules in the main
        guppylang language package. Set to False if you want to resolve calling frames
        in e.g. the std lib.
    """
    frame = inspect.currentframe()
    while frame:
        module = inspect.getmodule(frame)
        if module is None:
            return frame
        elif _is_main_lang_module(module):
            if not skip_main_lang:
                return frame
        elif _is_internals_module(module):
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
            _is_main_lang_module(module) or _is_internals_module(module)
        ):
            return remove_internal_frames(tb.tb_next)
        if tb.tb_next:
            tb.tb_next = remove_internal_frames(tb.tb_next)
    return tb


def _is_main_lang_module(module: ModuleType) -> bool:
    return module.__name__.startswith("guppylang.")


def _is_internals_module(module: ModuleType) -> bool:
    return module.__name__.startswith("guppylang_internals.")
