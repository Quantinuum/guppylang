from guppylang import guppy
from guppylang.std.builtins import array, owned, result
from guppylang.std.quantum import cx, h, measure, qubit


def ranges_flat_array():
    """Version of `ranges` with flattened control flow but retaining array accesses"""

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

    @guppy
    def f(qs: array[qubit, 4] @ owned) -> array[qubit, 4]:
        h(qs[0])
        h(qs[3])
        h(qs[2])
        h(qs[1])

        cx(qs[0], qs[1])
        cx(qs[1], qs[2])
        cx(qs[2], qs[3])

        cx(qs[2], qs[3])
        cx(qs[1], qs[2])
        cx(qs[0], qs[1])

        h(qs[1])
        h(qs[0])
        h(qs[3])
        h(qs[2])
        return qs

    return main.with_minimal_opt().compile()
