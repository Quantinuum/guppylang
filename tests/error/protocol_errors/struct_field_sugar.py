from guppylang import guppy

@guppy.protocol
class Proto:
    @guppy.require
    def foo(self: "Proto") -> None:
        ...


@guppy.struct
class Ty:
    @guppy
    def foo(self) -> None:
        pass

@guppy.struct(frozen=True)
class S:
    p: Proto # This should fail with a nice error

@guppy
def foo(s: S) -> None:
    pass

@guppy
def main() -> None:
    foo(S(Ty()))

main.compile()
g
