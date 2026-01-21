"""Minimal test for direct enum recursion detection.

This test manually creates enum definitions to test the check_not_recursive
function without requiring the @guppy.enum decorator.
"""

import ast

import pytest
from guppylang_internals.checker.core import Globals
from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.enum import (
    ParsedEnumDef,
    UncheckedEnumVariant,
    check_not_recursive,
)
from guppylang_internals.error import GuppyError
from guppylang_internals.tys.parsing import TypeParsingCtx


def test_direct_recursion():
    """Test that direct recursion is detected."""
    # Create a fake enum that references itself
    # This simulates: class MyEnum: Variant: MyEnum
    # Create AST for the type annotation "MyEnum"
    type_ast = ast.Name(id="MyEnum", ctx=ast.Load())
    # Create the enum definition
    defn = ParsedEnumDef(
        id=DefId.fresh(),
        name="MyEnum",
        defined_at=ast.ClassDef(
            name="MyEnum",
            bases=[],
            keywords=[],
            body=[],
            decorator_list=[],
        ),
        params=[],
        variants=[UncheckedEnumVariant("Variant", [type_ast])],
    )
    # Register it so type_from_ast can find it
    globals_dict = {"MyEnum": defn}
    globals = Globals(globals_dict)
    ctx = TypeParsingCtx(globals, {})
    # This should raise GuppyError about recursive enums
    with pytest.raises(GuppyError, match="Recursive enums"):
        check_not_recursive(defn, ctx)

