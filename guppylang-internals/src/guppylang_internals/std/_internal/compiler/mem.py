from hugr import Wire, ops

from guppylang_internals.definition.custom import CustomInoutCallCompiler
from guppylang_internals.definition.value import CallReturnWires


class WithOwnedCompiler(CustomInoutCallCompiler):
    """Compiler for the `with_owned` function."""

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [val, func] = args
        [out, val] = self.builder.add_op(ops.CallIndirect(), func, val)
        return CallReturnWires(regular_returns=[out], inout_returns=[val])
