"""Test that mutually recursive enum definitions are rejected.

EnumA contains EnumB, and EnumB contains EnumA, creating a cycle.
"""

from guppylang.decorator import guppy


@guppy.enum
class EnumA:
    """First enum in mutual recursion."""
    Variant1 = {"items": "list[EnumB]"}


@guppy.enum
class EnumB:
    """Second enum in mutual recursion - should fail."""
    Variant1 = {"value": EnumA}


# This should raise an error when compiling EnumB
EnumB.compile()  # type: ignore[attr-defined]
