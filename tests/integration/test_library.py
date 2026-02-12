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

    @guppy
    def func_2() -> None:
        pass

    library = guppy.library(
        func_1,
        func_2,
    )

    compiled_library = library.compile()
    validate(compiled_library)
    assert _func_names(compiled_library) == {"func_1", "func_2"}
