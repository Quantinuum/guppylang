from guppylang import guppy
from guppylang.std.builtins import result, nat, array, comptime
from tests.util import compile_guppy


def test_basic(validate):
    @compile_guppy
    def main(x: int) -> None:
        result("foo", x)

    validate(main)


def test_multi(validate):
    @compile_guppy
    def main(w: nat, x: int, y: float, z: bool) -> None:
        result("a", w)
        result("b", x)
        result("c", y)
        result("d", z)

    validate(main)


def test_array(validate):
    @compile_guppy
    def main(
        w: array[nat, 42], x: array[int, 5], y: array[float, 1], z: array[bool, 0]
    ) -> None:
        result("a", w)
        result("b", x)
        result("c", y)
        result("d", z)

    validate(main)


# This caused problems with hugr (see https://github.com/Quantinuum/hugr/pull/2779),
# as it makes the linearizer copy an array (indeed, two arrays of different lengths).
def test_array_consts(run_int_fn):
    @guppy
    def main() -> int:
        result("x", array(True, False))
        result("y", array(False, True, False, False, True))
        return 3

    run_int_fn(main, 3)


def test_array_generic(validate):
    n = guppy.nat_var("n")

    @guppy
    def main(
        w: array[nat, n], x: array[int, n], y: array[float, n], z: array[bool, n]
    ) -> None:
        result("a", w)
        result("b", x)
        result("c", y)
        result("d", z)

    validate(main.compile_function())


def test_array_drop_after_result(validate):
    @compile_guppy
    def main() -> None:
        result("a", array(1, 2, 3))

    validate(main)


def test_same_tag(validate):
    @compile_guppy
    def main(x: int, y: float, z: bool) -> None:
        result("foo", x)
        result("foo", y)
        result("foo", z)

    validate(main)


def test_comptime_tag_inside(validate):
    @compile_guppy
    def main(x: int) -> None:
        result(comptime("a" + "b"), x)

    validate(main)


def test_comptime_tag_outside1(validate):
    EXAMPLE_RESULTS = [
        ("boolean", False),
        ("int", 123),
    ]

    @guppy.comptime
    def main() -> None:
        for key, value in EXAMPLE_RESULTS:
            result(key, value)

    validate(main.compile_function())


def test_comptime_tag_outside2(validate):
    EXAMPLE_RESULT = ("boolean", False)

    @guppy.comptime
    def main() -> None:
        result(EXAMPLE_RESULT[0], EXAMPLE_RESULT[1])

    validate(main.compile_function())
