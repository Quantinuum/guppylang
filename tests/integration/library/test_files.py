from hugr.package import Package

from guppylang import guppy
from guppylang.std.platform import result


def lib_hugr() -> Package:

    @guppy(link_name="lib1.my_super_adder")
    def super_adder_impl(x: int) -> int:
        return x + x

    lib = guppy.library(super_adder_impl).compile()
    return lib


def test_import_headers():
    from .lib1 import super_adder

    @guppy
    def main() -> None:
        result("result", super_adder(5))

    results = main.emulator(n_qubits=1, libs=[lib_hugr()]).run().results[0].entries
    assert results == [("result", 10)]
