"""Guppy standard module for debug functionality."""

# mypy: disable-error-code="empty-body, no-untyped-def"

from guppylang_internals.decorator import custom_function
from guppylang_internals.std._internal.debug import StateOutputChecker
from guppylang_internals.tys import Effect


@custom_function(
    checker=StateOutputChecker(),
    higher_order_value=False,
    has_var_args=True,
    effects=[Effect.OUTPUT],
)
def state_output(tag, *args) -> None:
    """Report the quantum state of the specified qubits.

    This is a debugging function that works only when the program is executed
    on a supported simulator.

    Guppy does not in general respect the order of function calls in the source code, it
    is constrained by the dataflow of the program. Whilst two `state_output`s are
    guaranteed to execute in source-code order, function calls such as "pure quantum"
    gates that act on disjoint qubits can slide past each other. This can interact badly
    with entanglement since the guppy compiler does not know which qubits are entangled
    together. That is, a gate on a qubit may execute before (or after) a `state_output`
    on another (potentially entangled) qubit, even when the gate occurs after (resp.
    before) the `state_output` in the source code. which can lead to unexpected results.
    To avoid this, use the :py:func:`barrier` command to ensure that all operations on a
    set of qubits are completed before the state is output.

    Args:
        tag: A string literal representing the tag of the state output.
        args: The qubits whose quantum state is to be reported. The order they are given
            in corresponds to the order in which the state will be reported.
    """


# Deprecated alias for `state_output`, deprecated since guppylang v1.0.
state_result = state_output
