from guppylang import guppy

@guppy.protocol
class Proto[T]:
    @guppy.require
    def foo(self: "Proto") -> T:
        ...


@guppy.struct
class Ty:
    @guppy
    def foo(self) -> int:
        pass

@guppy.struct(frozen=True)
class S:
    p: Proto[int] # This should fail with a nice error

@guppy
def foo(s: S) -> None:
    pass

@guppy
def main() -> None:
    foo(S(Ty()))

main.compile()
