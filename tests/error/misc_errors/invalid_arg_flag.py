from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


blah = owned


@guppy.declare
def foo(x: int @blah) -> qubit: ...


foo.compile()
