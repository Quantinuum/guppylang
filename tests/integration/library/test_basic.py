import pytest

from guppylang import guppy
from guppylang.defs import GuppyLibrary
from guppylang.emulator import EmulatorBuilder
from guppylang.std.platform import result
from guppylang.std.lang import comptime

from hugr._hugr.linking import HugrLinkingError


def gen_adder_library(*, name: str, value: int) -> GuppyLibrary:
    @guppy(link_name=name)
    def func(x: int) -> int:
        return x + comptime(value)

    return guppy.library(func)


def test_missing_impl():
    @guppy.declare(link_name="super_adder")
    def decl(x: int) -> int: ...

    @guppy
    def main() -> None:
        result("result", decl(5))

    with pytest.raises(
        RuntimeError,
        # On some platforms selene inserts an extra underscore
        match=r"undefined symbol: [_]?__hugr__.super_adder",
    ):
        main.emulator(n_qubits=1)


def test_missing_impl_existing_lib():
    """Asserts that even with a library that provides a function implementation, if the
    library is not explicitly included the function is still missing."""

    @guppy.declare(link_name="super_adder")
    def decl(x: int) -> int: ...

    _ = gen_adder_library(name="super_adder", value=10).compile()

    @guppy
    def main() -> None:
        result("result", decl(5))

    with pytest.raises(
        RuntimeError,
        # On some platforms selene inserts an extra underscore
        match=r"undefined symbol: [_]?__hugr__.super_adder",
    ):
        main.emulator(n_qubits=1)


def test_impl_provided():

    @guppy.declare(link_name="super_adder")
    def decl(x: int) -> int: ...

    adder_lib = gen_adder_library(name="super_adder", value=10).compile()

    @guppy
    def main() -> None:
        result("result", decl(5))

    emulator = main.emulator(n_qubits=1, libs=[adder_lib])
    results = emulator.run().results[0].entries
    assert results == [("result", 15)]


def test_impl_provided_second_lib():
    """Asserts that even with a second library that provides a function implementation,
    only including one library does not result in an error, and the correct
    implementation is used."""

    @guppy.declare(link_name="super_adder")
    def decl(x: int) -> int: ...

    adder_lib = gen_adder_library(name="super_adder", value=5).compile()
    _ = gen_adder_library(name="super_adder", value=20).compile()

    @guppy
    def main() -> None:
        result("result", decl(5))

    results = main.emulator(n_qubits=1, libs=[adder_lib]).run().results[0].entries
    assert results == [("result", 10)]


def test_unused_func_missing_impl():
    """Asserts that when a function is declared but not used (and so not included in the
    Hugr), it does not matter if the library is missing a function implementation."""

    @guppy.declare(link_name="func1")
    def decl_1(x: int) -> int: ...

    @guppy.declare(link_name="func2")
    def decl_2(x: int) -> int: ...

    @guppy(link_name="func1")
    def func(x: int) -> int:
        return x + 1

    # Missing an implementation for func2
    lib = guppy.library(func).compile()

    @guppy
    def main() -> None:
        result("result", decl_1(5))

    results = main.emulator(n_qubits=1, libs=[lib]).run().results[0].entries
    assert results == [("result", 6)]


def test_duplicate_defn():

    @guppy.declare(link_name="super_adder")
    def decl(x: int) -> int: ...

    adder_lib_1 = gen_adder_library(name="super_adder", value=5).compile()
    adder_lib_2 = gen_adder_library(name="super_adder", value=20).compile()

    @guppy
    def main() -> None:
        result("result", decl(5))

    with pytest.raises(
        HugrLinkingError,
        match=r"Source \(Node\([0-9]+\)\) and target \(Node\([0-9]+\)\) both contained FuncDefn with same public name super_adder",  # noqa: E501
    ):
        main.emulator(n_qubits=1, libs=[adder_lib_1, adder_lib_2])


def test_unused_func_duplicate_defn():
    """Asserts that duplicate definitions for unused functions still cause linkage to
    fail, since the resulting Hugr is not well-formed."""

    @guppy.declare(link_name="super_adder")
    def decl(x: int) -> int: ...

    lib_1 = gen_adder_library(name="super_adder", value=5).compile()
    lib_2 = gen_adder_library(name="super_adder", value=20).compile()

    @guppy
    def main() -> None:
        # Never use the decl
        result("result", 1)

    with pytest.raises(
        HugrLinkingError,
        match=r"Source \(Node\([0-9]+\)\) and target \(Node\([0-9]+\)\) both contained FuncDefn with same public name super_adder",  # noqa: E501
    ):
        main.emulator(n_qubits=1, libs=[lib_1, lib_2])


def test_pre_compile():
    @guppy.declare(link_name="super_adder")
    def decl(x: int) -> int: ...

    adder_lib = gen_adder_library(name="super_adder", value=10).compile()

    @guppy
    def main() -> None:
        result("result", decl(5))

    main_pkg = main.compile()

    emulator = EmulatorBuilder().build(main_pkg.link(adder_lib), n_qubits=1)
    results = emulator.run().results[0].entries
    assert results == [("result", 15)]


def test_dependency_public():
    """Tests that a library containing both a function and its dependency as public
    can be compiled and linked, even if the dependency is included after the depender.
    """

    @guppy
    def dependency_func(x: int) -> int:
        return 2 * x

    @guppy(link_name="adder")
    def depender_func(x: int) -> int:
        return x + dependency_func(x)

    # Including depender_func causes dependency to be emitted already
    lib = guppy.library(depender_func, dependency_func).compile()

    @guppy.declare(link_name="adder")
    def depender_func_decl(x: int) -> int: ...

    @guppy
    def main() -> None:
        result("result", depender_func_decl(5))

    main_pkg = main.compile()

    emulator = EmulatorBuilder().build(main_pkg.link(lib), n_qubits=1)
    results = emulator.run().results[0].entries
    assert results == [("result", 15)]
