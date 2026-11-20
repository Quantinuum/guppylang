"""Check custom power method declarations and signatures."""

import pytest

from guppylang import guppy
from guppylang.std.builtins import array, nat, owned
from guppylang.std.quantum import qubit
from guppylang_internals.engine import CustomModifiedDefSignatureError
from guppylang_internals.error import GuppyError


def test_power_methods_can_coexist():
    @guppy.unitary
    class gate:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def powered(q: qubit, exponent: nat) -> None:
            pass

        @guppy
        def power_daggered(q: qubit, exponent: nat) -> None:
            pass

        @guppy
        def ctrl_powered[n: nat](
            q: qubit, controls: array[qubit, n], exponent: nat
        ) -> None:
            pass

        @guppy
        def ctrl_power_daggered[n: nat](
            q: qubit, controls: array[qubit, n], exponent: nat
        ) -> None:
            pass

    gate.check()


def test_ctrl_power_daggered_can_be_the_only_override():
    @guppy.unitary
    class gate:
        @guppy
        def __call__[m: nat](qs: array[qubit, m]) -> None:
            pass

        @guppy
        def ctrl_power_daggered[n: nat, m: nat](
            qs: array[qubit, m], controls: array[qubit, n], exponent: nat
        ) -> None:
            pass

    gate.check()


def test_powered_requires_an_exponent():
    @guppy.unitary
    class gate:
        @guppy
        def __call__() -> None:
            pass

        @guppy
        def powered() -> None:
            pass

    with pytest.raises(GuppyError) as exc:
        gate.check()
    assert isinstance(exc.value.error, CustomModifiedDefSignatureError)


def test_power_daggered_preserves_parent_ownership():
    @guppy.unitary
    class gate:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def power_daggered(q: qubit @ owned, exponent: nat) -> None:
            pass

    with pytest.raises(GuppyError) as exc:
        gate.check()
    assert isinstance(exc.value.error, CustomModifiedDefSignatureError)


def test_ctrl_powered_requires_a_generic_control_count():
    @guppy.unitary
    class gate:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def ctrl_powered(q: qubit, controls: array[qubit, 2], exponent: nat) -> None:
            pass

    with pytest.raises(GuppyError) as exc:
        gate.check()
    assert isinstance(exc.value.error, CustomModifiedDefSignatureError)
