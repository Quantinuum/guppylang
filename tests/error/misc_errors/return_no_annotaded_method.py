"""Added after: https://github.com/Quantinuum/guppylang/issues/2204"""
from guppylang import guppy


@guppy.struct
class struct:

    @guppy
    def method():
        return

@guppy
def main() -> None:
    w = struct()
    w.method()


main.compile()