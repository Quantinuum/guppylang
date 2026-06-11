"""Controlling a function with internal control flow"""

from pathlib import Path
from sys import argv
import sys

from guppylang import guppy
from guppylang.std.builtins import control
from guppylang.std.debug import state_result
from guppylang.std.quantum import discard, h, qubit, rx, x, rz
from guppylang.std.angles import angle

sys.path.append(str(Path(__file__).resolve().parents[1]))

from guppylang.experimental import enable_experimental_features

enable_experimental_features()


@guppy(controllable=True)
def funz(t: qubit, a: angle) -> None:
    rz(t, a)


@guppy(controllable=True)
def branchy(q: qubit, flag: bool) -> None:
    if flag:
        x(q)
    else:
        h(q)


@guppy
def main() -> None:
    c = qubit()
    t = qubit()
    flag = True
    h(c)
    with control(c):
        inner_flag = False
        branchy(t, flag)
        branchy(t, inner_flag)
        a = angle(1 / 4)
        if flag:
            for _ in range(2):
                funz(t, a)
        if inner_flag:
            x(t)
        else:
            rot = 1 / 2
            while rot >= 1 / 4:
                rx(t, angle(rot))
                rot = rot / 2

    state_result("r", c, t)
    discard(c)
    discard(t)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
