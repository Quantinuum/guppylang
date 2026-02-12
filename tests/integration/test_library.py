from guppylang import guppy


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

    validate(library.compile())
