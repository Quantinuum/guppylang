from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.struct
class Struct:
    q: qubit

    @guppy
    def foo(self: "Struct @owned") -> "Struct":
        return self


@guppy
def foo(s: Struct @owned) -> Struct:
    f = s.foo
    return f()


foo.compile()
