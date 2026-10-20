"""Report a signature error for an unused custom `powered` method.

The override preserves its parent's inputs,
but the final exponent is int instead of nat. Checking the class must reject
this signature even though no modified call is made.
"""

from guppylang import guppy
from guppylang.std.quantum import qubit


@guppy.unitary
class gate:
    @guppy
    def __call__(q: qubit) -> None:
        pass

    @guppy
    def powered(q: qubit, exponent: int) -> None:
        pass


gate.check()
