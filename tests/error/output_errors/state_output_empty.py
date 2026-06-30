from guppylang.std.debug import state_output
from tests.util import compile_guppy

@compile_guppy
def main() -> None:
    state_output("tag")
