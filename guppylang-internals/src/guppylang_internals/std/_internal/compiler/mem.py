from hugr import Wire, ops

from guppylang_internals.ast_util import get_type
from guppylang_internals.compiler.expr_compiler import unpack_wire
from guppylang_internals.definition.custom import CustomInoutCallCompiler
from guppylang_internals.definition.value import CallReturnWires


class WithOwnedCompiler(CustomInoutCallCompiler):
    """Compiler for the `with_owned` function."""

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [val, func] = args
        [out, val] = self.builder.add_op(ops.CallIndirect(), func, val)
        outs = unpack_wire(out, get_type(self.node), self.builder, self.ctx)
        return CallReturnWires(regular_returns=outs, inout_returns=[val])
