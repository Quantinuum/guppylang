"""The string type."""

# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def"

from __future__ import annotations

from guppylang_internals.decorator import custom_function, extend_type
from guppylang_internals.std._internal.checker import UnsupportedChecker
from guppylang_internals.tys.builtin import string_type_def


@extend_type(string_type_def)
class str:
    """A string, i.e. immutable sequences of Unicode code points."""

    @custom_function(checker=UnsupportedChecker(), higher_order_value=False)
    def __new__(x): ...
