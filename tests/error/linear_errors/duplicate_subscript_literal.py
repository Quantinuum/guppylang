from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit, cx

import guppylang
guppylang.enable_experimental_features()


@guppy
def foo() -> None:
    external_reg = array((qubit() for _ in range(2)))
    cx(external_reg[0], external_reg[0])


foo.compile()
