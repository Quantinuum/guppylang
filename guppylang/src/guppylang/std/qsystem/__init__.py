"""Guppy standard library for Quantinuum systems device operations.

.. deprecated::
    ``guppylang.std.qsystem`` is a deprecated alias for
    ``guppylang.std.qsystem.helios``. Import from that module directly.
"""

from guppylang.std.qsystem.helios import (
    MaybeLeaked,
    collect_measurements,
    lazy_measure,
    lazy_measure_and_reset,
    lazy_measure_and_reset_array,
    lazy_measure_array,
    measure,
    measure_and_reset,
    measure_and_reset_array,
    measure_array,
    measure_leaked,
    phased_x,
    qfree,
    reset,
    rz,
    zz_max,
    zz_phase,
)
