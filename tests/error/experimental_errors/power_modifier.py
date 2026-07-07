from guppylang.decorator import guppy
from guppylang.std.builtins import power


@guppy
def main() -> None:
    with power(2):
        pass


main.compile_function()
