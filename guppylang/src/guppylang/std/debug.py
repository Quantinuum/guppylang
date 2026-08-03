"""Guppy standard module for debug functionality."""

# mypy: disable-error-code="empty-body, no-untyped-def"

from guppylang_internals.decorator import custom_function
from guppylang_internals.std._internal.debug import StateOutputChecker


@custom_function(
    checker=StateOutputChecker(),
    higher_order_value=False,
    has_var_args=True,
)
def state_output(tag, *args) -> None:
    """Report the quantum state of the specified qubits.

    This is a debugging function that works only when the program is executed
    on a supported simulator.

    Args:
        tag: A string literal representing the tag of the state output.
        args: The qubits whose quantum state is to be reported. The order they are given
        in corresponds to the order in which the state will be reported.
    """


# Deprecated alias for `state_output`, deprecated since guppylang v1.0.
state_result = state_output
