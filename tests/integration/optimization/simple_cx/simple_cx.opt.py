from guppylang import guppy
from guppylang.std.builtins import result


def simple_cx_opt():
    @guppy
    def main() -> None:
        result("b1", 0)
        result("b2", 0)

    return main.compile()
