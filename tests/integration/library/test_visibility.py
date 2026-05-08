from hugr.ops import FuncDefn, FuncDecl
from hugr.package import Package

from guppylang import guppy

import pytest


@pytest.fixture
def qualifier(request) -> str:
    """Provides the common qualifier for functions defined in the current test."""

    def tmp() -> None:
        pass

    return f"{tmp.__module__}.{request.node.originalname}"


def _func_names_and_visibilities(package: Package) -> set[tuple[str, str]]:
    hugr = package.modules[0]

    return {
        (n.op.f_name, n.op.visibility)
        for n in hugr.values()
        if isinstance(n.op, (FuncDefn, FuncDecl))
    }


def test_top_level_members_public(validate, qualifier):
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
        (f"{qualifier}.<locals>.func_1", "Public"),
        (f"{qualifier}.<locals>.func_2", "Public"),
        (f"{qualifier}.<locals>.MyStruct.member", "Public"),
        (f"{qualifier}.<locals>.MyStruct.member_decl", "Public"),
    }


def test_non_members_default_visibility(validate, qualifier):
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

    @guppy
    def main() -> None:
        # Use the functions to ensure they are included in the HUGR
        func_1()
        func_2()
        instance = MyStruct()
        instance.member()
        instance.member_decl()

    library = guppy.library(main)

    compiled_library = library.compile()
    validate(compiled_library)
    assert _func_names_and_visibilities(compiled_library) == {
        (f"{qualifier}.<locals>.main", "Public"),
        (f"{qualifier}.<locals>.func_1", "Private"),
        (f"{qualifier}.<locals>.func_2", "Public"),
        (f"{qualifier}.<locals>.MyStruct.member", "Private"),
        (f"{qualifier}.<locals>.MyStruct.member_decl", "Public"),
    }


def test_ensure_nested_members_private(validate, qualifier):
    @guppy
    def func_1() -> None:
        @guppy
        def nested_func() -> None:
            pass

        nested_func()

    @guppy.struct
    class MyStruct:
        @guppy
        def member(self) -> None:
            @guppy
            def nested_func() -> None:
                pass

            nested_func()

    @guppy
    def main() -> None:
        # Use the functions to ensure they are included in the HUGR
        func_1()
        instance = MyStruct()
        instance.member()

    library = guppy.library(main)

    compiled_library = library.compile()
    validate(compiled_library)
    assert _func_names_and_visibilities(compiled_library) == {
        (f"{qualifier}.<locals>.main", "Public"),
        (f"{qualifier}.<locals>.func_1", "Private"),
        # These collide in names in the HUGR, but for private functions the name has no
        # semantic impact. They are always private since we cannot reference them
        # outside their defining function, so they cannot be included in the public API
        # of a library.
        ("nested_func", "Private"),
        (f"{qualifier}.<locals>.MyStruct.member", "Private"),
    }
