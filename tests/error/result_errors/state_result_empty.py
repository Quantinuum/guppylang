from guppylang.std.debug import state_result
from tests.util import compile_guppy

@compile_guppy
def main() -> None:
    state_result("tag")
