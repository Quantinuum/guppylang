import pytest
from hugr.ops import FuncDefn

from guppylang import guppy
from guppylang.defs import GuppyDefinition
from guppylang.emulator import EmulatorBuilder
from guppylang.std.platform import result

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hugr.package import Package


def test_manual_link_no_entrypoints():
    @guppy.declare(link_name="super_adder")
    def decl(x: int) -> int: ...

    @guppy(link_name="super_adder")
    def impl(x: int) -> int:
        return x + 5

    lib1 = guppy.library(decl).compile()
    lib2 = guppy.library(impl).compile()

    @guppy
    def main() -> None:
        result("result", decl(5))

    linked = lib1.link(lib2)
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

    main_pkg: Package = main.compile()
    linked = main_pkg.link(adder_lib)
    assert linked.modules[0].entrypoint != linked.modules[0].module_root
    entrypoint = linked.modules[0].entrypoint_op()
    assert isinstance(entrypoint, FuncDefn)
    assert entrypoint.f_name.endswith(".main")

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

    main_pkg: Package = main.compile()
    linked = main_pkg.link(adder_lib)
    assert linked.modules[0].entrypoint != linked.modules[0].module_root
    entrypoint = linked.modules[0].entrypoint_op()
    assert isinstance(entrypoint, FuncDefn)
    assert entrypoint.f_name.endswith(".main")

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
