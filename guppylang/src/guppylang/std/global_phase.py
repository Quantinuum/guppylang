"""Guppy standard library for the global phase operation."""

# mypy: disable-error-code="empty-body, misc, override"

from typing import no_type_check

from guppylang_internals.decorator import custom_function
from guppylang_internals.std._internal.compiler.quantum import GlobalPhaseCompiler
from guppylang_internals.tys import Effect

from guppylang.std.angles import angle


@custom_function(GlobalPhaseCompiler(), effects=[Effect.ANY])
@no_type_check
def global_phase(angle: angle) -> None:
    """Apply a global phase to the circuit.

    This has no observable effect on its own, but becomes observable when the
    enclosing operation is controlled.
    """
