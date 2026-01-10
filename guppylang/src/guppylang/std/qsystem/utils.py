"""Guppy standard library for utilities available on Quantinuum
Systems."""

from typing import no_type_check

from guppylang_internals.decorator import hugr_op
from guppylang_internals.std._internal.compiler.tket_exts import QSYSTEM_UTILS_EXTENSION
from guppylang_internals.std._internal.util import external_op


@hugr_op(external_op("GetCurrentShot", [], ext=QSYSTEM_UTILS_EXTENSION))
@no_type_check
def get_current_shot() -> int:
    """Get the current shot number."""
