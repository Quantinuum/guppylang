"""Functional wrappers for Quantinuum Sol system operations.

These gates are the same as those in ``guppylang.std.qsystem.sol`` but use
functional syntax (owned qubits are taken and returned rather than borrowed).
"""

from typing import no_type_check

import guppylang.std.qsystem.sol as sol
from guppylang.decorator import guppy
from guppylang.std.angles import angle
from guppylang.std.builtins import owned
from guppylang.std.qsystem._functional_base import _make_shared_functional
from guppylang.std.quantum import qubit

# Inject shared ops (phased_x, rz, measure, measure_and_reset, reset, qfree,
# lazy_measure_and_reset, measure_array, measure_and_reset_array,
# lazy_measure_and_reset_array) from the factory.
globals().update(_make_shared_functional(sol))


# ---------------------------------------------------------------------------
# Sol-specific 2-qubit gate
# ---------------------------------------------------------------------------


@guppy
@no_type_check
def phased_xx(
    q1: qubit @ owned, q2: qubit @ owned, angle1: angle, angle2: angle
) -> tuple[qubit, qubit]:
    """Functional PhasedXX gate command. The native 2-qubit entangling gate on Sol."""
    sol.phased_xx(q1, q2, angle1, angle2)
    return q1, q2
