"""Tools for inspecting source code when running in IPython."""


def is_running_ipython() -> bool:
    """Checks if we are currently running in IPython"""
    try:
        return get_ipython() is not None  # type: ignore[name-defined]
    except NameError:
        return False


def normalize_ipython_dummy_files(filename: str) -> str:
    """Turns dummy file names generated for IPython cells into readable names like
    "<In[42]>".

    In vanilla IPython, cells have filenames like "<ipython-input-3-3e9b5833de21>" and
    in Jupyter, cells have filenames like "/var/{...}/ipykernel_82076/61218616.py".
    """
    try:
        if shell := get_ipython():  # type: ignore[name-defined]
            res = shell.compile.format_code_name(filename)
            if res is None:
                return filename
            return f"<{res[1]}>"
        else:
            return filename
    except NameError:
        return filename
