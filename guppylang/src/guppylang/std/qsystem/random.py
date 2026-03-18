"""Guppy standard library for random number generation and
discrete probability distributions."""

# mypy: disable-error-code="no-any-return"
from typing import Generic, no_type_check

from guppylang_internals.decorator import custom_function, custom_type, hugr_op
from guppylang_internals.std._internal.compiler.qsystem import (
    RandomIntBoundedCompiler,
    RandomIntCompiler,
)
from guppylang_internals.std._internal.compiler.quantum import (
    RNGCONTEXT_T,
)
from guppylang_internals.std._internal.compiler.tket_exts import (
    QSYSTEM_RANDOM_EXTENSION,
)
from guppylang_internals.std._internal.util import external_op

from guppylang import guppy
from guppylang.std.angles import angle, pi
from guppylang.std.array import array_swap
from guppylang.std.builtins import array, owned, panic
from guppylang.std.option import Option

SHUFFLE_N = guppy.nat_var("SHUFFLE_N")
SHUFFLE_T = guppy.type_var("SHUFFLE_T", copyable=False, droppable=False)

DISCRETE_N = guppy.nat_var("DISCRETE_N")


@hugr_op(external_op("NewRNGContext", [], ext=QSYSTEM_RANDOM_EXTENSION))
@no_type_check
def _new_rng_context(seed: int) -> Option["RNG"]: ...


@custom_type(RNGCONTEXT_T, copyable=False, droppable=False)
class RNG:
    """Random number generator."""

    @guppy  # type: ignore[misc] # Unsupported decorated constructor type; Self argument missing for a non-static method (or an invalid type for self)
    def __new__(seed: int) -> "RNG":  # noqa: PYI034
        """Create a new random number generator using a seed."""
        return _new_rng_context(seed).unwrap()

    @guppy
    def random_angle(self: "RNG") -> angle:
        r"""Generate a random angle in the range :math:`[-\pi, \pi)`."""
        return (2.0 * self.random_float() - 1.0) * pi

    @guppy
    def random_clifford_angle(self: "RNG") -> angle:
        r"""Generate a random Clifford angle (multiple of :math:`\pi/2`)."""
        return self.random_int_bounded(4) * pi / 2

    @hugr_op(external_op("DeleteRNGContext", [], ext=QSYSTEM_RANDOM_EXTENSION))
    @no_type_check
    def discard(self: "RNG" @ owned) -> None:
        """Discard the random number generator."""

    @custom_function(RandomIntCompiler())
    @no_type_check
    def random_int(self: "RNG") -> int:
        """Generate a random 32-bit signed integer."""

    @hugr_op(external_op("RandomFloat", [], ext=QSYSTEM_RANDOM_EXTENSION))
    @no_type_check
    def random_float(self: "RNG") -> float:
        """Generate a random floating point value in the range [0,1)."""

    @custom_function(RandomIntBoundedCompiler())
    @no_type_check
    def random_int_bounded(self: "RNG", bound: int) -> int:
        """Generate a random 32-bit integer in the range [0, bound).

        Args:
            bound: The upper bound of the range, needs to less than 2^31.
        """

    @hugr_op(external_op("RandomAdvance", [], ext=QSYSTEM_RANDOM_EXTENSION))
    @no_type_check
    def random_advance(self: "RNG", delta: int) -> None:
        """Advance or backtrack the RNG state by a given number of steps.

        Args:
            delta: Number of steps to move the RNG state forward (if positive)
            or backward (if negative).
        """

    @guppy
    @no_type_check
    def shuffle(self: "RNG", array: array[SHUFFLE_T, SHUFFLE_N]) -> None:
        """Randomly shuffle the elements of a possibly linear array in place.
        Uses the Fisher-Yates algorithm."""
        for k in range(SHUFFLE_N):
            i = SHUFFLE_N - 1 - k
            j = self.random_int_bounded(i + 1)
            if i != j:
                array_swap(array, i, j)


@guppy.struct
class DiscreteDistribution(Generic[DISCRETE_N]):  # type: ignore[misc]
    """A generic probability distribution over a set of the form {0, 1, ..., N-1}.

    Objects of this class should be generated using
    :py:meth:`make_discrete_distribution`.
    """

    # The `sums` array represents the cumulative probability distribution. That is,
    # sums[i] is the probability of drawing a value <= i from the distribution.
    sums: array[float, DISCRETE_N]  # type: ignore[valid-type]

    @guppy
    @no_type_check
    def sample(self: "DiscreteDistribution[DISCRETE_N]", rng: RNG) -> int:
        """Return a sample value from the distribution, using the provided
        :py:class:`RNG`.
        """
        x = rng.random_float()
        # Use binary search to find the least i s.t. sums[i] >= x.
        i_min = 0
        i_max = DISCRETE_N - 1
        while i_min < i_max:
            i = (i_min + i_max) // 2
            if self.sums[i] >= x:
                i_max = i
            else:
                i_min = i + 1
        return i_min


@guppy
@no_type_check
def make_discrete_distribution(
    weights: array[float, DISCRETE_N],
) -> DiscreteDistribution[DISCRETE_N]:
    """Construct a discrete probability distribution over the set
    {0, 1, 2, ... DISCRETE_N - 1}, given as an array of weights which represent
    probabilities. The weights need not be normalized, but must be non-negative and not
    all zero."""
    W = 0.0
    for w in weights.copy():
        if w < 0.0:
            panic("Negative weight included in discrete distribution.")
        W += w
    if W == 0.0:
        panic("No positive weights included in discrete distribution.")
    sums = array(0.0 for _ in range(DISCRETE_N))
    s = 0.0
    for i in range(DISCRETE_N - 1):
        s += weights[i]
        sums[i] = s / W
    sums[DISCRETE_N - 1] = 1.0
    return DiscreteDistribution(sums)
