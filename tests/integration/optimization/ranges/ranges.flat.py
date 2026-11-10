from guppylang import guppy
from guppylang.std.builtins import array, owned, result
from guppylang.std.quantum import cx, h, measure, qubit


def ranges_flat():
    @guppy
    def main() -> None:
        q1, q2, q3, q4 = qubit(), qubit(), qubit(), qubit()
        q1, q2, q3, q4 = f(array(q1, q2, q3, q4))
        b1 = measure(q1)
        b2 = measure(q2)
        b3 = measure(q3)
        b4 = measure(q4)

        result("b1", b1.read())
        result("b2", b2.read())
        result("b3", b3.read())
        result("b4", b4.read())

    @guppy.comptime
    def f(qs: array[qubit, 4] @ owned) -> array[qubit, 4]:
        for i in range(4):
            h(qs[(-i) % 4])
        for i in range(3):
            cx(qs[i], qs[i + 1])
        for i in range(3):
            cx(qs[2 - i], qs[3 - i])
        for i in range(4):
            h(qs[(3 * i + 1) % 4])
        return qs

    return main.with_minimal_opt().compile()
