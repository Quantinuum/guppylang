import pytest

from hugr._hugr.linking import HugrLinkingError

from guppylang import guppy
from guppylang.library import link_name

from guppylang.defs import GuppyDefinition
from guppylang.emulator import EmulatorBuilder
from guppylang.library import GuppyLibrary
from guppylang.std.platform import output


def test_manual_link_no_entrypoints():
    @guppy.declare
    @link_name("super_adder")
    def decl(x: int) -> int: ...

    @guppy
    @link_name("super_adder")
    def impl(x: int) -> int:
        return x + 5

    lib1 = GuppyLibrary.from_members(decl).compile()
    lib2 = GuppyLibrary.from_members(impl).compile()

    linked = lib1.link(lib2)
    # Not an executable module
    assert linked.modules[0].entrypoint == linked.modules[0].module_root


def test_manual_link_entrypoint_lhs():
    @guppy.declare
    @link_name("super_adder")
    def decl(x: int) -> int: ...

    @guppy
    @link_name("super_adder")
    def impl(x: int) -> int:
        return x + 5

    adder_lib = GuppyLibrary.from_members(impl).compile()

    @guppy
    def main() -> None:
        output("result", decl(5))

    linked = main.compile().link(adder_lib)
    emulator = EmulatorBuilder().build(linked, n_qubits=1)
    assert emulator.run().results[0].entries == [("result", 10)]


def test_manual_link_entrypoint_rhs():
    @guppy.declare
    @link_name("super_adder")
    def decl(x: int) -> int: ...

    @guppy
    @link_name("super_adder")
    def impl(x: int) -> int:
        return x + 5

    adder_lib = GuppyLibrary.from_members(impl).compile()

    @guppy
    def main() -> None:
        output("result", decl(5))

    linked = adder_lib.link(main.compile())
    emulator = EmulatorBuilder().build(linked, n_qubits=1)
    assert emulator.run().results[0].entries == [("result", 10)]


def test_manual_link_multiple_entrypoints():
    def produce_entrypoint() -> GuppyDefinition:
        @guppy
        def main() -> None:
            output("result", 1)

        return main

    lib1 = produce_entrypoint().compile()
    lib2 = produce_entrypoint().compile()

    with pytest.raises(
        HugrLinkingError,
        match="Cannot link two modules with non-root entrypoints together",
    ):
        lib1.link(lib2)
