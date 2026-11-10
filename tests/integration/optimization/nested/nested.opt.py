from guppylang import guppy
from guppylang.std.builtins import result
from guppylang.std.quantum import measure, qubit


def nested_opt():
    @guppy
    def main() -> None:
        q1, q2, q3 = qubit(), qubit(), qubit()
        b1 = measure(q1)
        b2 = measure(q2)
        b3 = measure(q3)

        result("b1", b1.read())
        result("b2", b2.read())
        result("b3", b3.read())

    return main.compile()
