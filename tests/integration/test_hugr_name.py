import pytest
from hugr.ops import FuncDefn, FuncDecl
from hugr.package import Package

from guppylang import guppy


@pytest.fixture
def qualifier(request) -> str:
    """Provides the common qualifier for functions defined in the current test."""

    def tmp() -> None:
        pass

    return f"{tmp.__module__}.{request.node.originalname}"


def _func_names(package: Package) -> set[str]:
    hugr = package.modules[0]

    return {
        n.op.f_name for n in hugr.values() if isinstance(n.op, (FuncDefn, FuncDecl))
    }


def _func_names_excluding_main(package: Package, qualifier: str) -> set[str]:
    func_names = _func_names(package)
    try:
        func_names.remove(f"{qualifier}.<locals>.main")
    except KeyError:
        raise AssertionError(
            f"Main function name `{qualifier}.<locals>.main` not found in package."
        )

    return func_names


def test_func_hugr_name_annotated():
    """Asserts that annotated function `hugr_name`s are passed to the HUGR nodes."""

    @guppy(hugr_name="some.qualified.name")
    def main_def() -> None:
        pass

    @guppy.declare(hugr_name="some.other.qualified.name")
    def main_dec() -> None: ...

    assert _func_names(main_def.compile()) == {"some.qualified.name"}
    assert _func_names(main_dec.compile()) == {"some.other.qualified.name"}


def test_func_hugr_name_inferred(qualifier):
    """Asserts that inferred function `hugr_name`s are passed to the HUGR nodes."""

    @guppy
    def crazy_def() -> None:
        pass

    @guppy.declare
    def crazy_dec() -> None: ...

    assert _func_names(crazy_def.compile()) == {f"{qualifier}.<locals>.crazy_def"}
    assert _func_names(crazy_dec.compile()) == {f"{qualifier}.<locals>.crazy_dec"}


def test_struct_member_hugr_name_annotated(qualifier):
    """Asserts that inferred function `hugr_name`s are passed to the HUGR nodes."""

    @guppy.struct
    class MySuperbStruct:
        @guppy(hugr_name="totally_qualified_override_name")
        def some_name_that_is_crazy(self) -> None:
            pass

        @guppy.declare(hugr_name="superbly_qualified_override_name")
        def some_other_name_that_is_crazy(self) -> None: ...

    @guppy
    def main() -> None:
        # Use so they get compiled and included in the package
        a = MySuperbStruct()
        a.some_name_that_is_crazy()
        a.some_other_name_that_is_crazy()

    assert _func_names_excluding_main(main.compile(), qualifier) == {
        "totally_qualified_override_name",
        "superbly_qualified_override_name",
    }


def test_struct_member_hugr_name_inferred(qualifier):
    """Asserts that inferred function `hugr_name`s are passed to the HUGR nodes."""

    @guppy.struct
    class MySuperbStruct:
        @guppy
        def some_name_that_is_crazy(self) -> None:
            pass

        @guppy.declare
        def some_other_name_that_is_crazy(self) -> None: ...

    @guppy
    def main() -> None:
        # Use so they get compiled and included in the package
        a = MySuperbStruct()
        a.some_name_that_is_crazy()
        a.some_other_name_that_is_crazy()

    assert _func_names_excluding_main(main.compile(), qualifier) == {
        f"{qualifier}.<locals>.MySuperbStruct.some_name_that_is_crazy",
        f"{qualifier}.<locals>.MySuperbStruct.some_other_name_that_is_crazy",
    }


def test_struct_member_hugr_name_supported(qualifier):
    """Asserts that function `hugr_name`s of struct members that are derived through
    providing a `hugr_name` to the struct are correctly inferred."""

    @guppy.struct(hugr_name="my.superb.qualifier")
    class MySuperbStruct:
        @guppy
        def some_name_that_is_crazy(self) -> None:
            pass

        @guppy(hugr_name="the.override.still.works")
        def some_other_name_that_is_crazy(self) -> None:
            pass

    @guppy
    def main() -> None:
        # Use so they get compiled and included in the package
        a = MySuperbStruct()
        a.some_name_that_is_crazy()
        a.some_other_name_that_is_crazy()

    assert _func_names_excluding_main(main.compile(), qualifier) == {
        "my.superb.qualifier.some_name_that_is_crazy",
        "the.override.still.works",
    }


@guppy
def file_level_defn() -> None:
    pass


@guppy.declare
def file_level_decl() -> None: ...


@guppy.struct
class FileLevelStruct:
    @guppy
    def crazy_name_defn(self) -> None:
        pass

    @guppy.declare
    def crazy_name_decl(self) -> None: ...


def test_file_level_members(qualifier):
    """Asserts that file level function and struct member names qualify correctly."""

    @guppy
    def main() -> None:
        # Use so they get compiled and included in the package
        a = FileLevelStruct()
        a.crazy_name_defn()
        a.crazy_name_decl()
        file_level_decl()
        file_level_defn()

    assert _func_names_excluding_main(main.compile(), qualifier) == {
        "tests.integration.test_hugr_name.file_level_defn",
        "tests.integration.test_hugr_name.file_level_decl",
        "tests.integration.test_hugr_name.FileLevelStruct.crazy_name_defn",
        "tests.integration.test_hugr_name.FileLevelStruct.crazy_name_decl",
    }
