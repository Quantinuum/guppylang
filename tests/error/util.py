import importlib.util
import inspect
import pathlib
import re
import sys

import pytest
from hugr import tys
from hugr.tys import TypeBound

from guppylang_internals.decorator import custom_type
from tests.util import get_wasm_file

# Regular expression to match the `~~~~~^^^~~~` highlights that are printed in
# tracebacks from Python 3.11 onwards. We strip those out so we can use the same golden
# files for Python 3.10
TRACEBACK_HIGHLIGHT = re.compile(r" *~*\^\^*~*")

# Regular expression to match the bootstrapping source line inserted in tracebacks from
# Python 3.13 onwards in combination with using execnet (the backend of pytest-xdist) to
# run the test. We strip those out so we can use the same golden files for Python < 3.13
EXECNET_BOOTSTRAP = re.compile(
    r" *import sys;exec\(eval\(sys.stdin.readline\(\)\)\) *")


def filter_traceback_not_containing(s: str, disallowed_regex: re.Pattern[str]) -> str:
    result = []
    traceback_started = False
    for line in s.split("\n"):
        if line.startswith("Traceback (most recent call last):"):
            traceback_started = True
        if traceback_started and disallowed_regex.fullmatch(line):
            continue

        result.append(line)

    return "\n".join(result)


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
    sys.excepthook(exc_info.type, exc_info.value.with_traceback(tb), tb)

    err = capsys.readouterr().err
    wasm_module = get_wasm_file()
    err = err.replace(str(file), "$FILE").replace(wasm_module, "$WASM")
    # Strip the bootstrap included in the traceback by Python 3.13+ for parallel tests
    err = filter_traceback_not_containing(err, EXECNET_BOOTSTRAP)
    # Strip the error markers that are only present for Python 3.11+
    err = filter_traceback_not_containing(err, TRACEBACK_HIGHLIGHT)

    snapshot.snapshot_dir = str(file.parent)
    snapshot.assert_match(err, file.with_suffix(".err").name)


@custom_type(
    tys.Opaque(extension="", id="", args=[], bound=TypeBound.Copyable)
)
class NonBool:
    pass
