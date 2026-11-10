from guppylang import guppy
from guppylang.std.builtins import result


def angles_opt():
    @guppy
    def main() -> None:
        result("b", 0)

    return main.compile()
