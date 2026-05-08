import pytest

from guppylang import guppy
from guppylang.defs import GuppyDefinition
from guppylang.emulator import EmulatorBuilder
from guppylang.std.platform import result


def test_manual_link_no_entrypoints():
    @guppy.declare(link_name="super_adder")
    def decl(x: int) -> int: ...

    @guppy(link_name="super_adder")
    def impl(x: int) -> int:
        return x + 5

    lib1 = guppy.library(decl).compile()
    lib2 = guppy.library(impl).compile()

    linked = lib1.link(lib2)
    # Not an executable module
    assert linked.modules[0].entrypoint == linked.modules[0].module_root


def test_manual_link_entrypoint_lhs():
    @guppy.declare(link_name="super_adder")
    def decl(x: int) -> int: ...

    @guppy(link_name="super_adder")
    def impl(x: int) -> int:
        return x + 5

    adder_lib = guppy.library(impl).compile()

    @guppy
    def main() -> None:
        result("result", decl(5))

    linked = main.compile().link(adder_lib)
    emulator = EmulatorBuilder().build(linked, n_qubits=1)
    assert emulator.run().results[0].entries == [("result", 10)]


def test_manual_link_entrypoint_rhs():
    @guppy.declare(link_name="super_adder")
    def decl(x: int) -> int: ...

    @guppy(link_name="super_adder")
    def impl(x: int) -> int:
        return x + 5

    adder_lib = guppy.library(impl).compile()

    @guppy
    def main() -> None:
        result("result", decl(5))

    linked = adder_lib.link(main.compile())
    emulator = EmulatorBuilder().build(linked, n_qubits=1)
    assert emulator.run().results[0].entries == [("result", 10)]


def test_manual_link_multiple_entrypoints():
    def produce_entrypoint() -> GuppyDefinition:
        @guppy
        def main() -> None:
            result("result", 1)

        return main

    lib1 = produce_entrypoint().compile()
    lib2 = produce_entrypoint().compile()

    with pytest.raises(ValueError, match="Cannot link two executable modules together"):
        lib1.link(lib2)
