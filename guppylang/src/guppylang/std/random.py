"""Pure Guppy random number generation."""

# mypy: disable-error-code="no-any-return, misc, call-arg, call-overload, assignment"
from __future__ import annotations

from typing import no_type_check

from guppylang import guppy
from guppylang.std.num import nat


@guppy
@no_type_check
def _mask32(value: nat) -> nat:
    uint32_mask: nat = 4294967295
    return value & uint32_mask


@guppy
@no_type_check
def _uint32_to_signed(value: nat) -> int:
    """Convert a 32-bit unsigned value stored in a nat to a signed 32-bit int."""
    uint32_sign_bit: nat = 2147483648
    masked = _mask32(value)
    if masked >= uint32_sign_bit:
        return int(masked) - 4294967296
    return int(masked)


@guppy.struct
class PCG32:
    """A deterministic 32-bit random number generator using the PCG32 algorithm.

    Unlike :py:class:`guppylang.std.qsystem.random.RNG`, PCG32 keeps its state in a
    local Guppy value rather than in platform-global RNG state. Because Guppy structs
    are immutable, each draw returns an updated generator together with the value:

    .. code-block:: python

        rng = seeded_pcg32(1)
        rng, value = rng.next_int()
        rng, another = rng.next_int()

    Thread the returned ``rng`` through your program to keep random streams independent.
    """

    state: nat
    inc: nat

    @guppy
    @no_type_check
    def next_int(self: PCG32) -> tuple[PCG32, int]:
        """Advance the generator and return the updated state with a random value.

        Returns a signed 32-bit integer, matching the shape of
        :py:meth:`guppylang.std.qsystem.random.RNG.random_int`.
        """
        pcg32_mult: nat = 6364136223846793005
        old_state = self.state
        new_state = nat(old_state * pcg32_mult + self.inc)
        xorshifted = _mask32(((old_state >> nat(18)) ^ old_state) >> nat(27))
        rot = _mask32(old_state >> nat(59))
        rot_inv = _mask32((~rot + nat(1)) & nat(31))
        output = _mask32((xorshifted >> rot) | (xorshifted << rot_inv))
        return PCG32(new_state, self.inc), _uint32_to_signed(output)


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
    initstate = nat(42)
    initseq = nat(seed)
    inc = nat((initseq << nat(1)) | nat(1))
    rng = PCG32(nat(0), inc)
    rng, _ = rng.next_int()
    rng = PCG32(rng.state + initstate, rng.inc)
    rng, _ = rng.next_int()
    return rng
