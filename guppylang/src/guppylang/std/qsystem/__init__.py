"""Guppy standard library for Quantinuum systems device operations.


Sub-modules in this module provide low-level access to primitive operations on specific
Quantinuum hardware systems. These systems may vary in primitive quantum gate-set,
measurement and reset operations, and other platform level capabilities.
These sub-modules are intended for advanced users who need control over the specific
operations used in their programs.
To program in a platform-agnostic way, use the more abstract `std.quantum` module.
Gates and operations in this module are automatically decomposed to the target
platform when compiling for emulation or hardware execution.

.. deprecated::
    ``guppylang.std.qsystem`` is a deprecated alias for
    ``guppylang.std.qsystem.helios``. Import from that module directly.
"""

from guppylang.std.qsystem.helios import (
    MaybeLeaked,
    N,
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
