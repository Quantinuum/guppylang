"""Pure Guppy random number generation.

Implements the PCG32 (XSH-RR, 64/32) generator from the PCG family; see
https://www.pcg-random.org/ and the reference C code in pcg-c-basic.
"""

# mypy: disable-error-code="no-any-return, misc, call-arg, call-overload, assignment"
from __future__ import annotations

from typing import no_type_check

from guppylang import guppy
from guppylang.std.num import nat


@guppy
@no_type_check
def _mask32(value: nat) -> nat:
    # 2**32 - 1: keep only the low 32 bits (Guppy has no native uint32 type).
    uint32_mask: nat = 4294967295
    return value & uint32_mask


@guppy
@no_type_check
def _mask64(value: nat) -> nat:
    # 2**64 - 1: PCG32 keeps its state in a 64-bit word (see pcg32_random_r).
    uint64_mask: nat = 18446744073709551615
    return value & uint64_mask


@guppy
@no_type_check
def _uint32_to_signed(value: nat) -> int:
    """Convert a 32-bit unsigned value stored in a nat to a signed 32-bit int."""
    # 2**31: high bit of a 32-bit word; values at or above this map to negative ints.
    uint32_sign_bit: nat = 2147483648
    masked = _mask32(value)
    if masked >= uint32_sign_bit:
        # 2**32: reinterpret unsigned 32-bit output as signed (two's complement).
        return int(masked) - 4294967296
    return int(masked)


@guppy.struct
class PCG32:
    """A deterministic 32-bit random number generator using the PCG32 algorithm.

    Unlike :py:class:`guppylang.std.qsystem.random.RNG`, PCG32 keeps its state in a
    local Guppy value rather than in platform-global RNG state.

    .. code-block:: python

        rng = seeded_pcg32(1)
        value = rng.next_int()
        roll = rng.next_int_bounded(6)
        another = rng.next_int()
    """

    _state: nat
    _inc: nat

    @guppy
    @no_type_check
    def _next_uint32(self: PCG32) -> nat:
        """Advance the generator and return the next 32-bit output word."""
        # LCG multiplier N from the PCG paper / pcg32_random_r (64-bit state, 32-bit
        # output).
        pcg32_mult: nat = 6364136223846793005
        old_state = self._state
        self._state = _mask64(nat(old_state * pcg32_mult + self._inc))
        # XSH-RR output permutation: xor-shift then random rotate (see pcg32_random_r).
        xorshifted = _mask32(
            ((_mask64(old_state) >> nat(18)) ^ _mask64(old_state)) >> nat(27)
        )
        # oldstate >> 59 is at most 31 for 64-bit state; mask for safe hugr shifts.
        rot = _mask32(_mask64(old_state) >> nat(59)) & nat(31)
        rot_inv = _mask32(nat(32) - rot) & nat(31)
        return _mask32((xorshifted >> rot) | (xorshifted << rot_inv))

    @guppy
    @no_type_check
    def next_int(self: PCG32) -> int:
        """Advance the generator and return the updated state with a random value.

        Returns a signed 32-bit integer, matching the shape of
        :py:meth:`guppylang.std.qsystem.random.RNG.random_int`.
        """
        return _uint32_to_signed(self._next_uint32())

    @guppy
    @no_type_check
    def next_int_bounded(self: PCG32, bound: int) -> int:
        """Generate a uniformly random integer in ``[0, bound)``.

        Uses rejection sampling (``pcg32_boundedrand_r`` from the PCG reference) to
        avoid the bias introduced by ``next_int() % bound``.

        Args:
            bound: Upper bound (exclusive); must be positive and less than ``2**31``.

        Returns:
            A value in ``[0, bound)``, matching the shape of
            :py:meth:`guppylang.std.qsystem.random.RNG.random_int_bounded`.
        """
        # uint32_t threshold = -bound % bound in pcg32_boundedrand_r.
        two_to_32: nat = 4294967296
        threshold = _mask32(two_to_32 - _mask32(nat(bound))) % nat(bound)
        while True:
            r = self._next_uint32()
            if r >= threshold:
                return int(r % nat(bound))


@guppy
@no_type_check
def seeded_pcg32(seed: int) -> PCG32:
    """Create a new :py:class:`PCG32` generator from a seed value.

    The seed selects one of ``2**63`` possible PCG32 sequences. The same seed always
    produces the same stream of values. Different :py:class:`PCG32` values do not
    share state, so using one generator does not affect another.

    Args:
        seed: Sequence identifier used to initialize the generator.
    """
    # Default initstate from PCG reference examples (e.g. Rosetta Code PCG32 task).
    initstate = nat(42)
    initseq = nat(seed)
    # PCG requires an odd increment; initseq is the stream/sequence selector.
    inc = nat((initseq << nat(1)) | nat(1))
    # pcg32_srandom_r: advance twice after mixing initstate into state.
    rng = PCG32(nat(0), inc)
    rng.next_int()
    rng._state = _mask64(rng._state + initstate)
    rng.next_int()
    return rng
