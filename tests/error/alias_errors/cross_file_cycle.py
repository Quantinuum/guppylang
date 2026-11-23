from guppylang import guppy

import tests.error.alias_errors.modules.cycle_a as cycle_a


@guppy
def main(x: cycle_a.Alias1) -> cycle_a.Alias1:
    return x


main.compile_function()
