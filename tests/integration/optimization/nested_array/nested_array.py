from guppylang import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import cx, qubit


def nested_array():
    @guppy
    def main(arr: array[array[qubit, 5], 3]) -> None:
        cx(arr[0][1], arr[0][2])
        cx(arr[0][1], arr[0][2])

    return main.with_minimal_opt().compile_function()
