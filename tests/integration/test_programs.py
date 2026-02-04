from guppylang.decorator import guppy


def test_factorial(validate):
    @guppy
    def factorial1(x: int) -> int:
        acc = 1
        while x > 0:
            acc *= x
            x -= 1
        return acc

    @guppy
    def factorial2(x: int) -> int:
        if x == 0:
            return 1
        return factorial2(x - 1) * x

    @guppy
    def factorial3(x: int, acc: int) -> int:
        if x == 0:
            return acc
        return factorial3(x - 1, acc * x)

    validate(factorial1.compile_function(), name="factorial1")
    validate(factorial2.compile_function(), name="factorial2")
    validate(factorial3.compile_function(), name="factorial3")


def test_even_odd(validate):
    @guppy
    def is_even(x: int) -> bool:
        if x == 0:
            return True
        return is_odd(x - 1)

    @guppy
    def is_odd(x: int) -> bool:
        if x == 0:
            return False
        return is_even(x - 1)

    validate(is_odd.compile_function())
    validate(is_even.compile_function())
