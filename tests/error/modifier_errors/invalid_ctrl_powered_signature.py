"""Report a signature error for an unused custom `ctrl_powered` method.

The override preserves its parent's inputs and a generic borrowed control array,
but the final exponent is int instead of nat. Checking the class must reject
this signature even though no modified call is made.
"""

from guppylang import guppy
from guppylang.std.builtins import array, nat
from guppylang.std.quantum import qubit


@guppy.unitary
class gate:
    @guppy
    def __call__(q: qubit) -> None:
        pass

    @guppy
    def ctrl_powered[n: nat](
        q: qubit, controls: array[qubit, n], exponent: int
    ) -> None:
        pass


gate.check()
