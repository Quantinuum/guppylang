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


def test_structural_subtyping():
    @guppy.struct
    class Foo:
        x: int

    @guppy.struct
    class Bar:
        x: int

    @guppy.declare(link_name="my_name")
    def do_foo(f: Foo) -> int: ...

    @guppy(link_name="my_name")
    def do_foo_impl(f: Bar) -> int:
        return f.x

    lib = guppy.library(Bar, do_foo_impl).compile()

    @guppy
    def main() -> None:
        f = Foo(4)
        result("result", do_foo(f))

    results = main.emulator(n_qubits=1, libs=[lib]).run().results[0].entries
    assert results == [("result", 4)]
