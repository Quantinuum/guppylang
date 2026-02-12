from hugr.ops import FuncDefn, FuncDecl
from hugr.package import Package

from guppylang import guppy


def _func_names(package: Package) -> set[str]:
    hugr = package.modules[0]

    return {
        n.op.f_name for n in hugr.values() if isinstance(n.op, (FuncDefn, FuncDecl))
    }


def test_func_hugr_name_annotated():
    """Asserts that annotated HUGR func names are correctly passed to the HUGR nodes."""

    @guppy(hugr_name="some.qualified.name")
    def main_def() -> None:
        pass

    @guppy.declare(hugr_name="some.other.qualified.name")
    def main_dec() -> None: ...

    assert _func_names(main_def.compile()) == {"some.qualified.name"}
    assert _func_names(main_dec.compile()) == {"some.other.qualified.name"}


def test_func_hugr_name_inferred():
    """Asserts that inferred HUGR func names are correctly passed to the HUGR nodes."""

    @guppy
    def crazy_def() -> None:
        pass

    @guppy.declare
    def crazy_dec() -> None: ...

    assert _func_names(crazy_def.compile()) == {"crazy_def"}
    assert _func_names(crazy_dec.compile()) == {"crazy_dec"}


def test_struct_member_hugr_name_annotated():
    """Asserts that inferred HUGR func names are correctly passed to the HUGR nodes."""

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

    assert _func_names(main.compile()) == {
        "main",
        "totally_qualified_override_name",
        "superbly_qualified_override_name",
    }


def test_struct_member_hugr_name_inferred():
    """Asserts that inferred HUGR func names are correctly passed to the HUGR nodes."""

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

    assert _func_names(main.compile()) == {
        "main",
        "MySuperbStruct.some_name_that_is_crazy",
        "MySuperbStruct.some_other_name_that_is_crazy",
    }
