from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from hugr import ops
from hugr.build.dfg import DfBase

from guppylang_internals.ast_util import AstNode, with_loc, with_type
from guppylang_internals.cfg.builder import tmp_vars
from guppylang_internals.checker.core import ComptimeVariable, Context, Locals, Variable
from guppylang_internals.checker.errors.type_errors import TypeMismatchError
from guppylang_internals.compiler.core import CompilerContext, DFContainer
from guppylang_internals.compiler.expr_compiler import ExprCompiler
from guppylang_internals.definition.value import CallableDef
from guppylang_internals.diagnostic import Error
from guppylang_internals.error import GuppyComptimeError, GuppyError, exception_hook
from guppylang_internals.nodes import PlaceNode
from guppylang_internals.tracing.builtins_mock import mock_builtins
from guppylang_internals.tracing.object import GuppyObject
from guppylang_internals.tracing.state import (
    TracingState,
    get_tracing_state,
    set_tracing_state,
)
from guppylang_internals.tracing.unpacking import (
    P,
    guppy_object_from_py,
    unpack_guppy_object,
    update_packed_value,
)
from guppylang_internals.tracing.util import capture_guppy_errors, tracing_except_hook
from guppylang_internals.tys.ty import FunctionType, InputFlags, type_to_row, unify

if TYPE_CHECKING:
    import ast

    from hugr import Wire


@dataclass(frozen=True)
class TracingReturnError(Error):
    title: ClassVar[str] = "Error in comptime function return"
    message: ClassVar[str] = "{msg}"
    msg: str


def trace_function(
    python_func: Callable[..., Any],
    ty: FunctionType,
    builder: DfBase[P],
    ctx: CompilerContext,
    node: AstNode,
) -> None:
    """Kicks off tracing of a function.

    Invokes the passed Python callable and constructs the corresponding Hugr using the
    passed builder.
    """
    state = TracingState(ctx, DFContainer(builder, ctx, {}), node)
    with set_tracing_state(state):
        inputs = [
            unpack_guppy_object(
                GuppyObject(inp.ty, wire),
                builder,
                # Function inputs are only allowed to be mutable if they are borrowed.
                # For owned arguments, mutation wouldn't be observable by the caller,
                # thus breaking the semantics expected from Python.
                frozen=InputFlags.Inout not in inp.flags,
            )
            for wire, inp in zip(builder.inputs(), ty.inputs, strict=True)
        ]

        with exception_hook(tracing_except_hook), mock_builtins(python_func):
            py_out = python_func(*inputs)

        try:
            out_obj = guppy_object_from_py(py_out, builder, node, ctx)
        except GuppyComptimeError as err:
            # Error in the return statement. For example, this happens if users
            # try to return a struct with invalid field values or there is a linearity
            # violation.
            raise GuppyError(TracingReturnError(node, str(err))) from None

        # Check that the output type is correct
        if unify(out_obj._ty, ty.output, {}) is None:
            raise GuppyError(
                TypeMismatchError(node, ty.output, out_obj._ty, "return value")
            )

        # Unpack regular returns
        out_tys = type_to_row(out_obj._ty)
        if len(out_tys) > 1:
            regular_returns: list[Wire] = list(
                builder.add_op(ops.UnpackTuple(), out_obj._use_wire(None)).outputs()
            )
        elif len(out_tys) > 0:
            regular_returns = [out_obj._use_wire(None)]
        else:
            regular_returns = []

        # Compute the inout extra outputs
        inout_returns = []
        assert ty.input_names is not None
        for inout_obj, inp, name in zip(inputs, ty.inputs, ty.input_names, strict=True):
            if InputFlags.Inout in inp.flags:
                err_prefix = (
                    f"Argument `{name}` is borrowed, so it is implicitly returned to "
                    f"the caller. "
                )
                try:
                    obj = guppy_object_from_py(inout_obj, builder, node, ctx)
                    inout_returns.append(obj._use_wire(None))
                except GuppyComptimeError as err:
                    msg = str(err)
                    if not msg.endswith("."):
                        msg += "."
                    e = TracingReturnError(node, err_prefix + msg)
                    raise GuppyError(e) from None
                # Also check that the type hasn't changed (for example, the user could
                # have changed the length of an array, thus changing its type)
                if obj._ty != inp.ty:
                    msg = (
                        f"{err_prefix}Expected it to have type `{inp.ty}`, but got "
                        f"`{obj._ty}`."
                    )
                    e = TracingReturnError(node, msg)
                    raise GuppyError(e) from None

    # Check that all allocated linear objects have been used
    if state.unused_undroppable_objs:
        _, unused = state.unused_undroppable_objs.popitem()
        msg = f"Value with non-droppable type `{unused._ty}` is leaked by this function"
        raise GuppyError(TracingReturnError(node, msg)) from None

    builder.set_outputs(*regular_returns, *inout_returns)


@capture_guppy_errors
def trace_call(func: CallableDef, *args: Any) -> Any:
    """Handles calls to Guppy functions during tracing.

    Checks that the passed arguments match the signature of the function and also
    handles inout arguments.
    """
    state = get_tracing_state()

    # Try to turn args into `GuppyObjects`
    args_objs = [
        guppy_object_from_py(arg, state.dfg.builder, state.node, state.ctx)
        for arg in args
    ]

    # Create dummy variables and bind the objects to them
    arg_vars: list[Variable] = [
        ComptimeVariable(next(tmp_vars), obj._ty, None, static_value=arg)
        for (obj, arg) in zip(args_objs, args, strict=True)
    ]
    locals = Locals({var.name: var for var in arg_vars})
    for obj, var in zip(args_objs, arg_vars, strict=True):
        state.dfg[var] = obj._use_wire(func)

    # Check call
    arg_exprs: list[ast.expr] = [
        with_loc(state.node, with_type(var.ty, PlaceNode(var))) for var in arg_vars
    ]
    call_node, ret_ty = func.synthesize_call(
        arg_exprs, state.node, Context(state.globals, locals, {})
    )

    # Compile call
    ret_wire = ExprCompiler(state.ctx).compile(call_node, state.dfg)

    # Update inouts
    # If the input types of the function aren't known, we can't check this.
    # This is the case for functions with a custom checker and no type annotations.
    if len(func.ty.inputs) != 0:
        for inp, arg, var in zip(func.ty.inputs, args, arg_vars, strict=True):
            if InputFlags.Inout in inp.flags:
                # Note that `inp.ty` could refer to bound variables in the function
                # signature. Instead, make sure to use `var.ty` which will always be a
                # concrete type and type checking has ensured that they unify.
                ty = var.ty
                inout_wire = state.dfg[var]
                success = update_packed_value(
                    arg, GuppyObject(ty, inout_wire), state.dfg.builder
                )
                if not success:
                    # This means the user has passed an object that we cannot update,
                    # e.g. calling `mem_swap(x, y)` where the inputs are plain Python
                    # objects
                    raise GuppyComptimeError(
                        f"Cannot borrow Python object of type `{ty}` at comptime"
                    )

    ret_obj = GuppyObject(ret_ty, ret_wire)
    return unpack_guppy_object(ret_obj, state.dfg.builder)
