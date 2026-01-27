"""Test that direct recursive enum definitions are rejected.

This enum contains itself directly, which would create an infinite type.
"""

from guppylang.decorator import guppy


@guppy.enum
class MyEnum:
    """An enum that contains itself - should fail."""
    Variant1: "tuple[MyEnum, int]"


# This should raise an error during compilation
MyEnum.compile()
