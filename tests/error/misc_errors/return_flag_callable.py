from typing import Callable

from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.declare
def foo(f: "Callable[[], qubit @owned]") -> None: ...


foo.compile()
