from guppylang import guppy
from guppylang.std.platform import result


def test_struct_defn():
    @guppy.struct(link_name="super_struct")
    class MyStruct:
        @guppy
        def super_func(self) -> int:
            return 5

    lib = guppy.library(MyStruct).compile()

    @guppy.struct(link_name="super_struct")
    class MyStructInterface:
        @guppy.declare
        def super_func(self) -> int: ...

    @guppy
    def main() -> None:
        m = MyStructInterface()
        result("result", m.super_func())

    results = main.emulator(n_qubits=1, libs=[lib]).run().results[0].entries
    assert results == [("result", 5)]
