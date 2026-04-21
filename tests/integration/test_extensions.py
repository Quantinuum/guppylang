from guppylang.std.array import array
from guppylang_internals.tys.common import ToHugrContext
from guppylang_internals.tys.subst import Inst

from tests.util import compile_guppy
from typing import no_type_check
from collections.abc import Callable

from hugr import ext, tys, ops
from guppylang.decorator import hugr_op
import tket_exts


def custom_ext_op(
    op_name: str,
    extension: ext.Extension,
) -> Callable[[tys.FunctionType, Inst, ToHugrContext], ops.DataflowOp]:
    """Utility method to create guppy operations from user-defined extensions.

    args:
        op_name: The name of the operation.
        ext: The extension of the operation.

    Returns:
        A function that takes an instantiation of the type arguments and returns
        a concrete HUGR op.
    """
    op_def = extension.get_op(op_name)

    def op(ty: tys.FunctionType, inst: Inst, ctx: ToHugrContext) -> ops.DataflowOp:
        return ops.ExtOp(
            op_def,
            ty,
            args=[],
        )

    return op


def test_custom_extension(validate):

    opaque_bool_ty = tket_exts.bool.bool_t

    # Build an extension with a custom op
    op_def = ext.OpDef(
        name="CustomOp",
        description="outer op with lowering",
        signature=ext.OpDefSig(tys.FunctionType.endo([opaque_bool_ty])),
    )
    extension = ext.Extension(
        version=ext.Version(0, 1, 0),
        name="outer",
        types={},
    )
    extension.add_op_def(op_def)

    @hugr_op(custom_ext_op("CustomOp", extension))
    @no_type_check
    def custom_op(b: bool) -> bool:
        """Opaque boolean map."""

    @compile_guppy
    def ret(b: bool) -> array[bool, 1]:
        res = custom_op(b)
        return array(res)

    assert {ext.name for ext in ret.extensions} == {
        "outer",
        "tket.bool",
    }
    assert ret.modules[0].used_extensions().used_extensions.ids() == {
        "prelude",
        "collections.array",
        "collections.borrow_arr",
        "outer",
        "tket.bool",
    }

    validate(ret)
