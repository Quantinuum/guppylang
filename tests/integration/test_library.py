from hugr.ops import FuncDefn, FuncDecl
from hugr.package import Package

from guppylang import guppy


# TODO deduplicate
def _func_names(package: Package) -> set[str]:
    hugr = package.modules[0]

    return {
        n.op.f_name for n in hugr.values() if isinstance(n.op, (FuncDefn, FuncDecl))
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

    library = guppy.library(
        func_1,
        func_2,
        MyStruct,
    )

    compiled_library = library.compile()
    validate(compiled_library)
    assert _func_names(compiled_library) == {
        "tests.integration.test_library.test_smoke_test_library.<locals>.func_1",
        "tests.integration.test_library.test_smoke_test_library.<locals>.func_2",
        "tests.integration.test_library.test_smoke_test_library.<locals>.MyStruct.member",
    }
