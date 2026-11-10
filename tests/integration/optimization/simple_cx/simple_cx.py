from guppylang import guppy
from guppylang.std.builtins import result
from guppylang.std.quantum import cx, measure, qubit


def simple_cx():
    @guppy
    def main() -> None:
        q1, q2 = qubit(), qubit()
        cx(q1, q2)
        cx(q1, q2)
        b1 = measure(q1)
        b2 = measure(q2)

        result("b1", b1.read())
        result("b2", b2.read())

    return main.with_minimal_opt().compile()
