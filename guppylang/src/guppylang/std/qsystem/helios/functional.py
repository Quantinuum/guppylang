"""Functional wrappers for Quantinuum Helios system operations.

These gates are the same as those in ``guppylang.std.qsystem.helios`` but use
functional syntax (owned qubits are taken and returned rather than borrowed).
"""

from typing import no_type_check

import guppylang.std.qsystem.helios as helios
from guppylang.decorator import guppy
from guppylang.std.angles import angle
from guppylang.std.builtins import owned
from guppylang.std.qsystem._functional_base import _make_shared_functional
from guppylang.std.quantum import qubit

# Inject shared ops (phased_x, rz, measure, measure_and_reset, reset, qfree,
# lazy_measure_and_reset, measure_array, measure_and_reset_array,
# lazy_measure_and_reset_array) from the factory.
globals().update(_make_shared_functional(helios))


# ---------------------------------------------------------------------------
# Helios-specific 2-qubit gate
# ---------------------------------------------------------------------------


@guppy
@no_type_check
def zz_phase(q1: qubit @ owned, q2: qubit @ owned, angle: angle) -> tuple[qubit, qubit]:
    """Functional ZZPhase gate command."""
    helios.zz_phase(q1, q2, angle)
    return q1, q2


@guppy
@no_type_check
def zz_max(q1: qubit @ owned, q2: qubit @ owned) -> tuple[qubit, qubit]:
    """Functional ZZMax gate command."""
    helios.zz_max(q1, q2)
    return q1, q2
