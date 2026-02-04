import builtins
import re

import pytest

from guppylang.decorator import guppy
from guppylang.std.builtins import array


def test_float(validate):
    @guppy.comptime
    def test(x: int) -> float:
        # Make sure that the mocked float is indistinguishable from the real deal
        assert isinstance(4.0, float)
        assert isinstance(4.0, builtins.float)
        assert isinstance(float(4), float)
        assert isinstance(float(4), builtins.float)
        assert isinstance(float, type)
        assert issubclass(float, float)
        assert issubclass(float, builtins.float)
        assert issubclass(builtins.float, float)
        assert float == builtins.float  # noqa: E721
        assert not float != builtins.float  # noqa: E721
        assert float.__name__ == builtins.float.__name__
        assert float.__qualname__ == builtins.float.__qualname__

        for v in (True, False, -42, 1.5, "-0.42"):
            assert float(v) == builtins.float(v)

        # But they are not identical
        assert float is not builtins.float

        # In particular, `builtins.float` doesn't work for GuppyObjects, but our mocked
        # version does
        err = re.escape("GuppyObject.__float__ returned non-float (type GuppyObject)")
        with pytest.raises(TypeError, match=err):
            builtins.float(x)
        return float(x)

    validate(test.compile_function())

    # Outside the function, we have the regular builtin
    assert float is builtins.float


def test_int(validate):
    @guppy.comptime
    def test(x: float) -> int:
        # Make sure that the mocked int is indistinguishable from the real deal
        assert isinstance(4, int)
        assert isinstance(4, builtins.int)
        assert isinstance(int(4.0), int)
        assert isinstance(int(4.0), builtins.int)
        assert isinstance(int, type)
        assert issubclass(int, int)
        assert issubclass(int, builtins.int)
        assert issubclass(builtins.int, int)
        assert issubclass(bool, int)
        assert int == builtins.int  # noqa: E721
        assert not int != builtins.int  # noqa: E721
        assert int.__name__ == builtins.int.__name__
        assert int.__qualname__ == builtins.int.__qualname__

        for v in (True, False, 42, "-123"):
            assert int(v) == builtins.int(v)
        assert int("1000", 2) == builtins.int("1000", 2)

        # But they are not identical
        assert int is not builtins.int

        # In particular, `builtins.int` doesn't work for GuppyObjects, but our mocked
        # version does
        err = re.escape("__int__ returned non-int (type GuppyObject)")
        with pytest.raises(TypeError, match=err):
            builtins.int(x)
        return int(x)

    validate(test.compile_function())

    # Outside the function, we have the regular builtin
    assert int is builtins.int


def test_len(validate):
    @guppy.struct
    class S:
        x: int

        @guppy
        def __len__(self: "S") -> int:
            return self.x

    @guppy.comptime
    def test(xs: array[int, 10]) -> int:
        # Make sure that the mocked len is indistinguishable from the real deal
        assert len([1, 2, 3, 4, 5]) == 5
        assert len({1, 2}) == 2
        assert len({1: 1}) == 1
        assert len(()) == 0
        assert len(xs) == 10

        # But they are not identical
        assert len != builtins.len
        assert len is not builtins.len

        # In particular, `builtins.len` doesn't work for GuppyObjects, but our mocked
        # version does
        s = S(100)
        err = re.escape("object of type 'GuppyStructObject' has no len()")
        with pytest.raises(TypeError, match=err):
            builtins.len(s)
        return len(s)

    validate(test.compile_function())

    # Outside the function, we have the regular builtin
    assert len is builtins.len
