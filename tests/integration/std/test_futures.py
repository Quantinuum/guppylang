from guppylang.decorator import guppy
from guppylang.std.futures import Future
from guppylang.std.lang import owned


def test_read(validate):
    @guppy
    def main(x: Future[int], y: Future[bool] @ owned) -> int:
        z = x.copy()
        if y.read():
            return z.read()
        z.discard()
        return 0

    validate(main.compile_function())
