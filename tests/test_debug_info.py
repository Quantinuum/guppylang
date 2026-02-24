from guppylang_internals.debug_info import HugrDebugInfo

from guppylang import guppy


def test_compile_unit():
    @guppy
    def foo() -> None:
        pass

    hugr = foo.compile().modules[0]
    meta = hugr.module_root.metadata
    assert HugrDebugInfo.KEY in meta
