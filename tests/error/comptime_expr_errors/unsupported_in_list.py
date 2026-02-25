import random
import numpy as np
from guppylang import guppy
from guppylang.std.builtins import comptime
from guppylang.std.qsystem.utils import get_current_shot
from guppylang.std.quantum import qubit, discard

randints = list(np.random.choice(3, 50, p = [0.1, 0.5, 0.4]))

@guppy
def main() -> None:
    q = qubit()
    randval = comptime(randints)[get_current_shot()]
    discard(q)

main.compile()