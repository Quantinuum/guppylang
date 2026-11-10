import pytest

from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.builtins import control, dagger, power
from guppylang.std.num import nat
from guppylang.std.quantum import h, measure, qubit
from guppylang_internals.error import GuppyError
from guppylang_internals.tys.errors import UnitaryCallError


def test_control_index_checked_in_outer_dagger(use_experimental_features):
    @guppy
    def nested(cs: array[qubit, 2], q: qubit) -> None:
        with dagger:
            with control(cs[int(measure(qubit()).read())]):
                h(q)

    with pytest.raises(GuppyError) as exc:
        nested.check()
    assert isinstance(exc.value.error, UnitaryCallError)


def test_power_argument_checked_in_outer_dagger(use_experimental_features):
    @guppy
    def nested(q: qubit) -> None:
        with dagger:
            with power(nat(int(measure(qubit()).read()))):
                h(q)

    with pytest.raises(GuppyError) as exc:
        nested.check()
    assert isinstance(exc.value.error, UnitaryCallError)


def test_control_index_not_checked_with_inner_dagger(use_experimental_features):
    @guppy
    def nested(cs: array[qubit, 2], q: qubit) -> None:
        with control(cs[int(measure(qubit()).read())]):
            with dagger:
                h(q)

    nested.check()


def test_power_argument_not_checked_with_inner_dagger(use_experimental_features):
    @guppy
    def nested(q: qubit) -> None:
        with power(nat(int(measure(qubit()).read()))):
            with dagger:
                h(q)

    nested.check()


def test_control_index_checked_before_nested_dagger_cancels(use_experimental_features):
    @guppy
    def nested(cs: array[qubit, 2], q: qubit) -> None:
        with dagger:
            with dagger, control(cs[int(measure(qubit()).read())]):
                h(q)

    with pytest.raises(GuppyError) as exc:
        nested.check()
    assert isinstance(exc.value.error, UnitaryCallError)


def test_power_argument_checked_before_nested_dagger_cancels(use_experimental_features):
    @guppy
    def nested(q: qubit) -> None:
        with dagger:
            with dagger, power(nat(int(measure(qubit()).read()))):
                h(q)

    with pytest.raises(GuppyError) as exc:
        nested.check()
    assert isinstance(exc.value.error, UnitaryCallError)


def test_control_index_not_checked_with_same_block_dagger(use_experimental_features):
    @guppy
    def nested(cs: array[qubit, 2], q: qubit) -> None:
        with dagger, control(cs[int(measure(qubit()).read())]):
            h(q)

    nested.check()


def test_power_argument_not_checked_with_same_block_dagger(use_experimental_features):
    @guppy
    def nested(q: qubit) -> None:
        with dagger, power(nat(int(measure(qubit()).read()))):
            h(q)

    nested.check()
