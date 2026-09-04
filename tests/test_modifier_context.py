"""Unit tests for modifier call-site context logic."""

import pytest
from guppylang_internals.checker.modifier import (
    CustomModifierKind,
    ModifierContext,
)
from guppylang_internals.tys.builtin import nat_type
from guppylang_internals.tys.const import BoundConstVar, ConstValue


def test_compose_uses_dagger_xor_and_concatenates_control_sizes():
    outer = ModifierContext(daggered=True, control_sizes=(1,))
    inner = ModifierContext(daggered=True, control_sizes=(2, 3))

    assert outer.compose(inner) == ModifierContext(
        daggered=False,
        control_sizes=(1, 2, 3),
    )


def test_concrete_control_count_sums_ints_and_const_values():
    modifiers = ModifierContext(
        control_sizes=(1, ConstValue(nat_type(), 2), 3),
    )

    assert modifiers.concrete_control_count() == 6


def test_concrete_control_count_rejects_symbolic_const():
    modifiers = ModifierContext(
        control_sizes=(BoundConstVar(nat_type(), "n", 0),),
    )

    with pytest.raises(ValueError, match="Control count is not concrete"):
        modifiers.concrete_control_count()


@pytest.mark.parametrize(
    ("modifiers", "expected"),
    [
        (ModifierContext(), None),
        (ModifierContext(daggered=True), CustomModifierKind.DAGGERED),
        (ModifierContext(control_sizes=(1,)), CustomModifierKind.CONTROLLED),
        (
            ModifierContext(daggered=True, control_sizes=(1,)),
            CustomModifierKind.CTRL_DAGGERED,
        ),
    ],
)
def test_kind_required(
    modifiers: ModifierContext,
    expected: CustomModifierKind | None,
):
    assert modifiers.kind_required() == expected


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        (CustomModifierKind.DAGGERED, False),
        (CustomModifierKind.CONTROLLED, True),
        (CustomModifierKind.CTRL_DAGGERED, True),
    ],
)
def test_custom_modifier_kind_takes_controls(
    kind: CustomModifierKind,
    expected: bool,
):
    assert kind.takes_controls is expected
