"""Guppy standard module for debug functionality."""

# mypy: disable-error-code="empty-body, no-untyped-def"

from guppylang_internals.decorator import custom_function
from guppylang_internals.std._internal.debug import StateResultChecker


@custom_function(checker=StateResultChecker(), higher_order_value=False)
def state_result(tag, *args) -> None:
    """Report the quantum state of the specified qubits.

    This is a debugging function that works only when the program is executed
    on a supported simulator.

    Args:
        tag: A string literal representing the tag of the result.
        args: The qubits whose quantum state is to be reported. The order they are given
        in corresponds to the order in which the state will be reported.
    """
