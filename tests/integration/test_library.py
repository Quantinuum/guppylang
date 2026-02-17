from hugr.ops import FuncDefn, FuncDecl
from hugr.package import Package

from guppylang import guppy


def _func_names_and_visibilities(package: Package) -> set[tuple[str, str]]:
    hugr = package.modules[0]

    return {
        (n.op.f_name, n.op.visibility)
        for n in hugr.values()
        if isinstance(n.op, (FuncDefn, FuncDecl))
    }


def test_smoke_test_library(validate):
    @guppy
    def func_1() -> None:
        pass

    @guppy.declare
    def func_2() -> None: ...

    @guppy.struct
    class MyStruct:
        @guppy
        def member(self) -> None:
            pass

        @guppy.declare
        def member_decl(self) -> None: ...

    library = guppy.library(
        func_1,
        func_2,
        MyStruct,
    )

    compiled_library = library.compile()
    validate(compiled_library)
    assert _func_names_and_visibilities(compiled_library) == {
        (
            "tests.integration.test_library.test_smoke_test_library.<locals>.func_1",
            "Public",
        ),
        (
            "tests.integration.test_library.test_smoke_test_library.<locals>.func_2",
            "Public",
        ),
        (
            "tests.integration.test_library.test_smoke_test_library.<locals>.MyStruct.member",
            "Public",
        ),
        (
            "tests.integration.test_library.test_smoke_test_library.<locals>.MyStruct.member_decl",
            "Public",
        ),
    }
