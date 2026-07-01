from hugr.ops import FuncDefn
from tket.metadata import InlineAnnotation

from guppylang_internals.definition.metadata import MetadataInline
from guppylang.decorator import guppy
from guppylang.std.builtins import result
from guppylang.std.quantum import (
    qubit,
    measure,
)


def test_hinted_inline(validate) -> None:
    @guppy(inline="best_effort")
    def main() -> None:
        result("c", measure(qubit()))

    compiled = main.compile_function()
    validate(compiled)

    hugr = compiled.modules[0]
    [fd] = [data for _, data in hugr.nodes() if isinstance(data.op, FuncDefn)]
    assert fd.metadata[MetadataInline.key] == "best_effort"
    assert fd.metadata[InlineAnnotation.KEY] == "best_effort"
