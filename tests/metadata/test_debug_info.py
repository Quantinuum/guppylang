from guppylang_internals.metadata.debug_info import HugrDebugInfo

from guppylang import guppy


def test_compile_unit():
    @guppy
    def foo() -> None:
        pass

    hugr = foo.compile().modules[0]
    meta = hugr.module_root.metadata
    assert HugrDebugInfo.KEY in meta


def test_subprogram():
    @guppy
    def foo() -> None:
        pass

    hugr = foo.compile().modules[0]
    func = hugr.children(hugr.module_root)[0]
    meta = func.metadata
    assert HugrDebugInfo.KEY in meta
