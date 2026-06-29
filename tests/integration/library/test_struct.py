from guppylang import guppy
from guppylang.library import link_name

from guppylang.library import GuppyLibrary
from guppylang.std.platform import output


def test_struct_defn():
    @guppy.struct
    @link_name("super_struct")
    class MyStruct:
        @guppy
        def super_func(self) -> int:
            return 5

    lib = GuppyLibrary.from_members(MyStruct).compile()

    @guppy.struct
    @link_name("super_struct")
    class MyStructInterface:
        @guppy.declare
        def super_func(self) -> int: ...

    @guppy
    def main() -> None:
        m = MyStructInterface()
        output("result", m.super_func())

    results = main.emulator(n_qubits=1, libs=[lib]).run().results[0].entries
    assert results == [("result", 5)]


def test_structural_subtyping():
    @guppy.struct
    class Foo:
        x: int

    @guppy.struct
    class Bar:
        x: int

    @guppy.declare
    @link_name("my_name")
    def do_foo(f: Foo) -> int: ...

    @guppy
    @link_name("my_name")
    def do_foo_impl(f: Bar) -> int:
        return f.x

    lib = GuppyLibrary.from_members(Bar, do_foo_impl).compile()

    @guppy
    def main() -> None:
        f = Foo(4)
        output("result", do_foo(f))

    results = main.emulator(n_qubits=1, libs=[lib]).run().results[0].entries
    assert results == [("result", 4)]
