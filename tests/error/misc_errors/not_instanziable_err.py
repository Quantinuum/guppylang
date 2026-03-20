from tests.util import compile_guppy 
from guppylang.std.builtins import frozenarray

@compile_guppy
def main() -> frozenarray[int, 3]:
    return frozenarray(1, 11, 21)
