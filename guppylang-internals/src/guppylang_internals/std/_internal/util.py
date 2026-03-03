"""Utilities for defining builtin functions.

Note: These custom definitions will be replaced with direct extension operation
definitions from the hugr library.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

import hugr.std.collections.list
import hugr.std.float
import hugr.std.int
import hugr.std.logic
from hugr import ext as he
from hugr import ops
from hugr import tys as ht

from guppylang_internals.compiler.hugr_extension import UnsupportedOp
from guppylang_internals.std._internal.compiler.tket_bool import OpaqueBool
from guppylang_internals.std._internal.compiler.tket_exts import (
    BOOL_EXTENSION,
    QUANTUM_EXTENSION,
)
from guppylang_internals.tys.common import ToHugrContext
from guppylang_internals.tys.subst import Inst
from guppylang_internals.tys.ty import NumericType

if TYPE_CHECKING:
    from guppylang_internals.tys.arg import Argument


def int_arg(n: int = NumericType.INT_WIDTH) -> ht.TypeArg:
    """A bounded int type argument."""
    return ht.BoundedNatArg(n=n)


def type_arg(idx: int = 0, bound: ht.TypeBound = ht.TypeBound.Linear) -> ht.TypeArg:
    """A generic type argument."""
    return ht.VariableArg(idx=idx, param=ht.TypeTypeParam(bound=bound))


def make_concrete_arg(
    arg: ht.TypeArg,
    inst: Inst,
    ctx: ToHugrContext,
    variable_remap: dict[int, int] | None = None,
) -> ht.TypeArg:
    """Makes a concrete hugr type argument using a guppy instantiation.

    Args:
        arg: The hugr type argument to make concrete, containing variable arguments.
        inst: The guppy instantiation of the type arguments.
        ctx: Context for the Guppy to Hugr type conversion.
        variable_remap: A mapping from the hugr param variable indices to
            de Bruijn indices in the guppy type. Defaults to identity.
    """
    remap = variable_remap or {}

    if isinstance(arg, ht.VariableArg) and remap.get(arg.idx, arg.idx) < len(inst):
        concrete_arg: Argument = inst[remap.get(arg.idx, arg.idx)]
        return concrete_arg.to_hugr(ctx)
    return arg


def external_op(
    name: str,
    args: list[ht.TypeArg],
    ext: he.Extension,
    *,
    variable_remap: dict[int, int] | None = None,
) -> Callable[[ht.FunctionType, Inst, ToHugrContext], ops.DataflowOp]:
    """Custom hugr operation

    Args:
        op_name: The name of the operation.
        args: The type arguments of the operation.
        ext: The extension of the operation.
        variable_remap: A mapping from the hugr param variable indices to
            de Bruijn indices in the guppy type. Defaults to identity.

    Returns:
        A function that takes an instantiation of the type arguments as well as
        the inferred input and output types and returns a concrete HUGR op.
    """
    op_def = ext.get_op(name)

    def op(ty: ht.FunctionType, inst: Inst, ctx: ToHugrContext) -> ops.DataflowOp:
        concrete_args = [
            make_concrete_arg(arg, inst, ctx, variable_remap) for arg in args
        ]
        return op_def.instantiate(concrete_args, ty)

    return op


def float_op(
    op_name: str,
    ext: he.Extension = hugr.std.float.FLOAT_OPS_EXTENSION,
) -> Callable[[ht.FunctionType, Inst, ToHugrContext], ops.DataflowOp]:
    """Utility method to create Hugr float arithmetic ops.

    Args:
        op_name: The name of the operation.
        ext: The extension of the operation.

    Returns:
        A function that takes an instantiation of the type arguments and returns
        a concrete HUGR op.
    """
    return external_op(op_name, args=[], ext=ext, variable_remap=None)


def int_op(
    op_name: str,
    ext: he.Extension = hugr.std.int.INT_OPS_EXTENSION,
    n_vars: int = 1,
) -> Callable[[ht.FunctionType, Inst, ToHugrContext], ops.DataflowOp]:
    """Utility method to create Hugr integer arithmetic ops.

    Args:
        op_name: The name of the operation.
        ext: The extension of the operation.
        n_vars: The number of type arguments. Defaults to 1.

    Returns:
        A function that takes an instantiation of the type arguments and returns
        a concrete HUGR op.
    """
    # Ideally we'd be able to derive the arguments from the input/output types,
    # but the amount of variables does not correlate with the signature for the
    # integer ops in hugr :/
    # https://github.com/quantinuum/hugr/blob/bfa13e59468feb0fc746677ea3b3a4341b2ed42e/hugr-core/src/std_extensions/arithmetic/int_ops.rs#L116
    #
    # For now, we just instantiate every type argument to a 64-bit integer.
    args: list[ht.TypeArg] = [int_arg() for _ in range(n_vars)]

    return external_op(
        op_name,
        args=args,
        ext=ext,
        variable_remap=None,
    )


def logic_op(
    op_name: str,
    parametric_size: bool = False,
    ext: he.Extension = hugr.std.logic.EXTENSION,
) -> Callable[[ht.FunctionType, Inst, ToHugrContext], ops.DataflowOp]:
    """Utility method to create Hugr logic ops.

    If `parametric_size` is True, the generated operations has a single argument
    encoding the number of boolean inputs to the operation.

    args:
        op_name: The name of the operation.
        parametric_size: Whether the input count is a parameter to the operation.
        ext: The extension of the operation.

    Returns:
        A function that takes an instantiation of the type arguments and returns
        a concrete HUGR op.
    """
    op_def = ext.get_op(op_name)

    def op(ty: ht.FunctionType, inst: Inst, ctx: ToHugrContext) -> ops.DataflowOp:
        args = [int_arg(len(ty.input))] if parametric_size else []
        return ops.ExtOp(
            op_def,
            ty,
            args,
        )

    return op


def list_op(
    op_name: str,
    ext: he.Extension = hugr.std.collections.list.EXTENSION,
) -> Callable[[ht.FunctionType, Inst, ToHugrContext], ops.DataflowOp]:
    """Utility method to create Hugr list ops.

    Args:
        op_name: The name of the operation.
        ext: The extension of the operation.

    Returns:
        A function that takes an instantiation of the type arguments and returns
        a concrete HUGR op.
    """
    op_def = ext.get_op(op_name)

    def op(ty: ht.FunctionType, inst: Inst, ctx: ToHugrContext) -> ops.DataflowOp:
        return ops.ExtOp(
            op_def,
            ty,
            [arg.to_hugr(ctx) for arg in inst],
        )

    return op


def quantum_op(
    op_name: str,
    ext: he.Extension = QUANTUM_EXTENSION,
) -> Callable[[ht.FunctionType, Inst, ToHugrContext], ops.DataflowOp]:
    """Utility method to create Hugr quantum ops.

    args:
        op_name: The name of the operation.
        ext: The extension of the operation.

    Returns:
        A function that takes an instantiation of the type arguments and returns
        a concrete HUGR op.
    """
    op_def = ext.get_op(op_name)

    def op(ty: ht.FunctionType, inst: Inst, ctx: ToHugrContext) -> ops.DataflowOp:
        return ops.ExtOp(
            op_def,
            ty,
            args=[],
        )

    return op


def unsupported_op(
    op_name: str,
) -> Callable[[ht.FunctionType, Inst, ToHugrContext], ops.DataflowOp]:
    """Utility method to define not-yet-implemented operations.

    Args:
        op_name: The name of the operation to define.

    Returns:
        A function that takes an instantiation of the type arguments as well as
        the inferred input and output types and returns a concrete HUGR op.
    """

    def op(ty: ht.FunctionType, inst: Inst, ctx: ToHugrContext) -> ops.DataflowOp:
        return UnsupportedOp(
            op_name=op_name,
            inputs=ty.input,
            outputs=ty.output,
        )

    return op


def bool_logic_op(
    op_name: str,
) -> Callable[[ht.FunctionType, Inst, ToHugrContext], ops.DataflowOp]:
    """Utility method to create binary `tket.bool` logic ops.

    args:
        op_name: The name of the operation.

    Returns:
        A function that takes an instantiation of the type arguments and returns
        a concrete HUGR op.
    """

    def op(ty: ht.FunctionType, inst: Inst, ctx: ToHugrContext) -> ops.DataflowOp:
        return ops.ExtOp(
            BOOL_EXTENSION.get_op(op_name),
            ht.FunctionType([OpaqueBool, OpaqueBool], [OpaqueBool]),
        )

    return op
