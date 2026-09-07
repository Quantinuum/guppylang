import pytest
from hugr import ops

from guppylang import guppy
from guppylang.decorator import inline
from guppylang.std.quantum import qubit, h, s


@pytest.mark.parametrize(
    ("annot", "expected_names"),
    [("best_effort", ["main"]), ("never", ["main", "inline_func"])],
)
def test_inline(annot: str, expected_names: list[str]) -> None:
    @guppy
    @inline(annot)
    def inline_func(q0: qubit) -> None:
        h(q0)

    @guppy
    def main(q0: qubit) -> None:
        inline_func(q0)
        s(q0)

    hugr = main.compile_function().modules[0]
    module_ops = [hugr[n].op for n in hugr[hugr.module_root].children]
    func_names = [op.f_name for op in module_ops if isinstance(op, ops.FuncDefn)]
    assert len(func_names) == len(expected_names)
    for name in expected_names:
        names_containing_expected = (1 for n in func_names if name in n)
        assert sum(names_containing_expected) == 1
