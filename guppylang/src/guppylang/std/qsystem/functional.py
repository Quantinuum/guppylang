"""Guppy standard module for functional qsystem native operations.

.. deprecated::
    ``guppylang.std.qsystem.functional`` is a deprecated alias for
    ``guppylang.std.qsystem.helios.functional``. Import from that module directly.
"""

from guppylang.std.qsystem.helios.functional import (  # noqa: F401
    N,
    lazy_measure_and_reset,
    lazy_measure_and_reset_array,
    measure,
    measure_and_reset,
    measure_and_reset_array,
    measure_array,
    phased_x,
    qfree,
    reset,
    rz,
    zz_max,
    zz_phase,
)
