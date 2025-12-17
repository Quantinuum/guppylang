import importlib.util
import inspect
import pathlib
import re
import sys

from guppylang_internals.decorator import custom_type
import pytest
import sys
from hugr import tys
from hugr.tys import TypeBound

import guppylang.decorator as decorator

from tests.util import get_wasm_file

# Regular expression to match the `~~~~~^^^~~~` highlights that are printed in
# tracebacks from Python 3.11 onwards. We strip those out so we can use the same golden
# files for Python 3.10
TRACEBACK_HIGHLIGHT = re.compile(r" *~*\^\^*~*")


def run_error_test(file, capsys, snapshot):
    file = pathlib.Path(file)

    with pytest.raises(Exception) as exc_info:
        importlib.import_module(f"tests.error.{file.parent.name}.{file.stem}")

    # Remove the importlib frames from the traceback by skipping beginning frames until
    # we end up in the executed file
    tb = exc_info.tb
    while tb is not None and inspect.getfile(tb.tb_frame) != str(file):
        tb = tb.tb_next

    # Invoke except hook to print the exception to stderr
    # sys.excepthook(exc_info.type, exc_info.value.with_traceback(tb), tb)

    from guppylang_internals.error import pretty_hook

    pretty_hook(exc_info.type, exc_info.value, tb)

    err = capsys.readouterr().err
    wasm_module = get_wasm_file()
    err = err.replace(str(file), "$FILE").replace(wasm_module, "$WASM")

    # If we're comparing tracebacks, strip the highlights that are only present for
    # Python 3.11+
    if err.startswith("Traceback (most recent call last):"):
        err = "\n".join(
            line for line in err.split("\n") if not TRACEBACK_HIGHLIGHT.fullmatch(line)
        )

    print("\n§§§§§\n")
    print("testing: \n", file, "\n\n")
    print(err)
    print("\n§§§§\n")

    snapshot.snapshot_dir = str(file.parent)
    snapshot.assert_match(err, file.with_suffix(".err").name)


@custom_type(tys.Opaque(extension="", id="", args=[], bound=TypeBound.Copyable))
class NonBool:
    pass
