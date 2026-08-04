from typing import no_type_check
from guppylang.decorator import guppy
from guppylang.module import GuppyModule

from guppylang.std.array import zip, enumerate
from guppylang.std.builtins import array


def test_zip(validate, run_int_fn):
    module = GuppyModule("test")
    module.load(zip)

    @guppy(module)
    @no_type_check
    def main() -> int:
        pyi = array(13, 2352, 358)
        pyb = array(True, False, True)

        total = 0
        for i, b in zip(pyi, pyb):
            total += i * (int(b) + 1)

        return total

    package = module.compile()
    validate(package)

    run_int_fn(package, expected=3094)


def test_enumerate(validate, run_int_fn):
    module = GuppyModule("test")
    module.load(enumerate)

    @guppy(module)
    @no_type_check
    def main() -> int:
        pyi = array(13, 2352, 358)

        total = 0
        for i, v in enumerate(pyi):
            total += v * (i + 1)

        return total

    package = module.compile()
    validate(package)

    run_int_fn(package, expected=5791)


if __name__ == "__main__":
    test_zip(None, None)
