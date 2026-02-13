from typing import no_type_check
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.array.bool import (
    array_eq,
    array_any,
    array_all,
    parity,
    bitwise_xor,
    pack_bits_dlo,
)
from guppylang.std.builtins import array


def test_bool_array_eq(validate, run_int_fn):
    module = GuppyModule("test")
    module.load(array_eq)

    @guppy(module)
    @no_type_check
    def main() -> int:
        yes = array_eq(array(True, False, True), array(True, False, True))
        no = not array_eq(array(True, False, True), array(False, True, False))

        return 2 * int(yes) + int(no)

    package = module.compile()
    validate(package)
    run_int_fn(package, expected=3)


def test_array_any(validate, run_int_fn) -> None:
    module = GuppyModule("test")
    module.load(array_any)

    @guppy(module)
    @no_type_check
    def main() -> int:
        yes = array_any(array(False, False, True))
        no = not array_any(array(False, False, False))

        return 2 * int(yes) + int(no)

    package = module.compile()
    validate(package)
    run_int_fn(package, expected=3)


def test_array_all(validate, run_int_fn) -> None:
    module = GuppyModule("test")
    module.load(array_all)

    @guppy(module)
    @no_type_check
    def main() -> int:
        yes = array_all(array(True, True, True))
        no = not array_all(array(True, False, True))

        return 2 * int(yes) + int(no)

    package = module.compile()
    validate(package)
    run_int_fn(package, expected=3)


def test_parity_check(validate, run_int_fn) -> None:
    module = GuppyModule("test")
    module.load(parity)

    @guppy(module)
    @no_type_check
    def main() -> int:
        yes = parity(array(True, True, True))
        no = not parity(array(True, False, True))

        return 2 * int(yes) + int(no)

    package = module.compile()
    validate(package)
    run_int_fn(package, expected=3)


def test_bitwise_xor(validate, run_int_fn) -> None:
    module = GuppyModule("test")
    module.load(bitwise_xor, array_eq)

    @guppy(module)
    @no_type_check
    def main() -> int:
        first = array_eq(
            bitwise_xor(array(True, False, True), array(False, True, True)),
            array(True, True, False),
        )
        second = array_eq(
            bitwise_xor(array(True, True, True), array(True, True, True)),
            array(False, False, False),
        )

        return 2 * int(first) + int(second)

    package = module.compile()
    validate(package)
    run_int_fn(package, expected=3)


def test_packbits_dlo(validate, run_int_fn) -> None:
    module = GuppyModule("test")
    module.load(pack_bits_dlo)

    @guppy(module)
    @no_type_check
    def main() -> int:
        five = pack_bits_dlo(array(True, False, True))
        four = pack_bits_dlo(array(True, False, False))
        empty = pack_bits_dlo(array())
        one = pack_bits_dlo(array(True))
        zero = pack_bits_dlo(array(False))
        two_zero = pack_bits_dlo(array(False, False))

        return five + four + empty + one + zero + two_zero

    package = module.compile()
    validate(package)
    run_int_fn(package, expected=10)
