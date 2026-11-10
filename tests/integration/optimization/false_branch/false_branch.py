from guppylang import guppy
from guppylang.std.builtins import result
from guppylang.std.quantum import h, measure, qubit


def false_branch():
    @guppy
    def main() -> None:
        q = qubit()
        h(q)
        if True:
            h(q)
        if False:
            h(q)
        b = measure(q).read()

        result("b", b)

    return main.with_minimal_opt().compile()
