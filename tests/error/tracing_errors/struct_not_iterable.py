from guppylang.decorator import guppy


@guppy.struct
class S:
    x: int

    @guppy.declare
    def __iter__(self: "S") -> int: ...


@guppy.comptime
def test() -> None:
    s = S(1)
    s.x = 1.0
    # Even though `S` implements `__iter__`, we can't use it during tracing
    for _ in s:
        pass


test.compile()
