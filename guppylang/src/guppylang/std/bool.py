"""Operations on booleans."""

# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def"

from __future__ import annotations

from typing import no_type_check

from guppylang_internals.decorator import custom_function, extend_type, hugr_op
from guppylang_internals.definition.custom import NoopCompiler
from guppylang_internals.std._internal.checker import DunderChecker, ReversingChecker
from guppylang_internals.std._internal.util import bool_logic_op
from guppylang_internals.tys.builtin import bool_type_def

from guppylang import guppy
from guppylang.std.num import nat


@extend_type(bool_type_def)
class bool:
    """Booleans representing truth values.

    The bool type has exactly two constant instances: ``True`` and ``False``.

    The bool constructor takes a single argument and converts it to ``True`` or
    ``False`` using the standard truth testing procedure.
    """

    @hugr_op(bool_logic_op("and"))
    def __and__(self: bool, other: bool) -> bool: ...

    @custom_function(NoopCompiler())
    def __bool__(self: bool) -> bool: ...

    @hugr_op(bool_logic_op("eq"))
    def __eq__(self: bool, other: bool) -> bool: ...

    @guppy
    @no_type_check
    def __ne__(self: bool, other: bool) -> bool:
        return not self == other

    @guppy
    @no_type_check
    def __int__(self: bool) -> int:
        return 1 if self else 0

    @guppy
    @no_type_check
    def __nat__(self: bool) -> nat:
        # TODO: Type information doesn't flow through the `if` expression, so we
        #  have to insert the `nat` coercions by hand.
        #  See https://github.com/quantinuum/guppylang/issues/707
        return nat(1) if self else nat(0)

    @custom_function(checker=DunderChecker("__bool__"), higher_order_value=False)
    def __new__(x): ...

    @hugr_op(bool_logic_op("or"))
    def __or__(self: bool, other: bool) -> bool: ...

    @hugr_op(bool_logic_op("xor"))
    def __xor__(self: bool, other: bool) -> bool: ...

    @custom_function(checker=ReversingChecker())
    def __rand__(self: bool, other: bool) -> bool: ...

    @custom_function(checker=ReversingChecker())
    def __ror__(self: bool, other: bool) -> bool: ...

    @custom_function(checker=ReversingChecker())
    def __rxor__(self: bool, other: bool) -> bool: ...
