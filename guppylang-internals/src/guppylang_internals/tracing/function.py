from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from guppylang_internals.ast_util import AstNode, with_loc, with_type
from guppylang_internals.cfg.builder import tmp_vars
from guppylang_internals.checker.core import (
    ComptimeVariable,
    Context,
    Globals,
    Locals,
    Variable,
)
from guppylang_internals.checker.errors.type_errors import TypeMismatchError
from guppylang_internals.checker.unitary_checker import BBUnitaryChecker
from guppylang_internals.compiler.builder.ops import unpack_tuple
from guppylang_internals.definition.custom import CustomFunctionDef
from guppylang_internals.definition.overloaded import OverloadedFunctionDef
from guppylang_internals.definition.value import CallableDef
from guppylang_internals.diagnostic import Error
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.error import (
    GuppyComptimeError,
    GuppyError,
    InternalGuppyError,
    RequiresMonomorphizationError,
    exception_hook,
)
from guppylang_internals.nodes import PlaceNode
from guppylang_internals.tracing.builtins_mock import mock_builtins
from guppylang_internals.tracing.object import GuppyObject
from guppylang_internals.tracing.state import (
    Trace,
    TraceableCall,
    TraceBuilder,
    TracingState,
    get_tracing_state,
    set_tracing_state,
)
from guppylang_internals.tracing.unpacking import (
    guppy_object_from_py,
    unpack_guppy_object,
    update_packed_value,
)
from guppylang_internals.tracing.util import capture_guppy_errors, tracing_except_hook
from guppylang_internals.tys.arg import Argument, ConstArg, TypeArg
from guppylang_internals.tys.const import BoundConstVar, ConstValue, ExistentialConstVar
from guppylang_internals.tys.ty import (
    BoundTypeVar,
    ExistentialTypeVar,
    FunctionType,
    InputFlags,
    UnitaryFlags,
    type_to_row,
    unify,
)

if TYPE_CHECKING:
    import ast

    from guppylang_internals.definition.traced import TracedFunctionDef
    from guppylang_internals.tys.common import ToHugrContext


@dataclass(frozen=True)
class TracingReturnError(Error):
    title: ClassVar[str] = "Error in comptime function return"
    message: ClassVar[str] = "{msg}"
    msg: str


def trace_function(
    python_func: Callable[..., Any],
    ty: FunctionType,
    input_count: int,
    generic_args: Mapping[str, Argument],
    node: AstNode,
    func_def: "TracedFunctionDef",
) -> Trace:
    """Kicks off tracing of a function.

    Invokes the passed Python callable and constructs the corresponding Hugr using the
    passed builder.
    """

    def const_argument_to_python_value(arg: Argument) -> Any:
        """Extracts a Python value from the given generic argument."""
        match arg:
            case ConstArg(ConstValue(value=v)):
                assert v is not None
                return v
            case (
                ConstArg(BoundConstVar())
                | ConstArg(ExistentialConstVar())
                | TypeArg(ty=BoundTypeVar())
            ):
                # This means we are building the arguments with which to trace
                # an uninstantiated generic function. So, avoid tracing such...
                raise RequiresMonomorphizationError
            case TypeArg(ty=ExistentialTypeVar()):
                raise InternalGuppyError("Shouldn't happen?!")
            case _:
                # TODO: We don't have a comptime representation of types yet, so we can
                #  only translate const arguments into Python values for now. In the
                #  future, drop this restriction and support all kinds of arguments.
                return None

    builder = TraceBuilder(input_count)
    ctx: ToHugrContext = None
    state = TracingState(ctx, builder, node, func_def)
    with set_tracing_state(state):
        generic_values = {
            x: val
            for x, arg in generic_args.items()
            if (val := const_argument_to_python_value(arg)) is not None
        }

        input_wires = iter(builder.inputs())
        inputs = []
        for inp in ty.inputs:
            if InputFlags.Comptime in inp.flags:
                assert inp.name is not None
                val = generic_values.pop(inp.name)
            else:
                # Function inputs are only allowed to be mutable if they are borrowed.
                # For owned arguments, mutation wouldn't be observable by the caller,
                # thus breaking the semantics expected from Python.
                frozen = InputFlags.Inout not in inp.flags
                val = unpack_guppy_object(
                    GuppyObject(inp.ty, next(input_wires)), builder, frozen
                )
            inputs.append(val)
        assert next(input_wires, None) is None, "All wires should be consumed"

        with (
            exception_hook(tracing_except_hook),
            mock_builtins(python_func),
            add_generic_to_function_globals(python_func, generic_values),
        ):
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
            regular_returns = list(
                builder.add_op(
                    unpack_tuple([out_ty.to_hugr(None) for out_ty in out_tys]),
                    out_obj._use_wire(None),
                ).outputs()
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
    return builder.finish()


def trace_call(func: CallableDef, *args: Any) -> Any:
    """Handles calls to Guppy functions during tracing.

    Checks that the passed arguments match the signature of the function and also
    handles inout arguments.
    """
    state = get_tracing_state()

    with capture_guppy_errors():
        # Try to turn args into `GuppyObjects`
        args_objs = [
            guppy_object_from_py(arg, state.builder, state.node, state.ctx)
            for arg in args
        ]

        # Create dummy variables and bind the objects to them
        arg_vars: list[Variable] = [
            ComptimeVariable(next(tmp_vars), obj._ty, None, static_value=arg)
            for (obj, arg) in zip(args_objs, args, strict=True)
        ]
        locals = Locals({var.name: var for var in arg_vars})

        input_places = [
            (var, obj._use_wire(func))
            for obj, var in zip(args_objs, arg_vars, strict=True)
        ]

        # Check call
        arg_exprs: list[ast.expr] = [
            with_loc(state.node, with_type(var.ty, PlaceNode(var))) for var in arg_vars
        ]
        ctx = Context(Globals(DEF_STORE.frames[func.id]), locals, {})
        call_node, ret_ty = func.synthesize_call(arg_exprs, state.node, ctx)

        # Here we check if unitary constraints are respected in the function body
        unitary_flag = state.function_definition.unitary_flags
        if unitary_flag != UnitaryFlags.NoFlags:
            unitary_checker = BBUnitaryChecker()
            unitary_checker.check([call_node], unitary_flag)

    # For overloaded functions, we first need to get the signature for the specific
    # overload that was used.
    resolved_func = func
    if len(resolved_func.ty.inputs) == 0 and isinstance(func, OverloadedFunctionDef):
        result = func.resolve_overload(arg_exprs, state.node, ctx)
        # Since we already type checked the call, this should always succeed.
        assert result is not None
        resolved_func = result

    input_flags: list[InputFlags] | None = None
    if len(resolved_func.ty.inputs) == len(args):
        input_flags = [inp.flags for inp in resolved_func.ty.inputs]

    # Custom functions without a signature or incomplete signature (e.g. varargs)
    # need to use `compute_input_flags` to determine the input flags.
    elif isinstance(resolved_func, CustomFunctionDef) and (
        not resolved_func.has_signature or resolved_func.has_var_args
    ):
        input_flags = resolved_func.call_checker.compute_input_flags(arg_exprs)
        assert len(input_flags) == len(args)

    else:
        raise InternalGuppyError(
            f"Couldn't compute signature for `{resolved_func.name}` during tracing. Add"
            " a signature to the function definition or provide an implementation of "
            "`compute_input_flags` in the call checker."
        )

    # Compile call
    output_count = len(type_to_row(ret_ty)) + sum(
        InputFlags.Inout in flags for flags in input_flags
    )
    assert isinstance(call_node, TraceableCall)
    call = state.builder.call(call_node, input_places, output_count)

    # Update inouts (normally done by ExprCompiler, but we need to do it here
    # so we can return meaningful GuppyObjects).
    inout_port = len(type_to_row(ret_ty))
    for flags, arg, var in zip(input_flags, args, arg_vars, strict=True):
        if InputFlags.Inout in flags:
            # Use `var.ty` as a concrete type when updating borrowed values.
            ty = var.ty
            inout_wire = call[inout_port]
            inout_port += 1
            success = update_packed_value(
                arg, GuppyObject(ty, inout_wire), state.builder
            )
            if not success:
                # This means the user has passed an object that we cannot update,
                # e.g. calling `mem_swap(x, y)` where the inputs are plain Python
                # objects
                raise GuppyComptimeError(
                    f"Cannot borrow Python object of type `{ty}` at comptime"
                )

    # Packing/unpacking, again paralleling ExprCompiler.
    regular_returns = list(call[: len(type_to_row(ret_ty))])
    if len(regular_returns) == 0:
        return None
    if len(regular_returns) == 1:
        r = GuppyObject(ret_ty, regular_returns[0])
        return unpack_guppy_object(r, state.builder)
    return tuple(
        unpack_guppy_object(GuppyObject(ty, ret), state.builder)
        for ret, ty in zip(regular_returns, type_to_row(ret_ty), strict=True)
    )


@contextmanager
def add_generic_to_function_globals(
    f: Callable[..., Any], generic_values: dict[str, Any]
) -> Iterator[None]:
    """Context manager that updates the given function to allow access to the
    instantiation of generic parameters."""
    # There are two ways a function can refer to a type variable. Variables defined on
    # module level via `guppy.type_var`, will be looked up in the functions'
    # `__globals__` table. Variables defined in a non-module parent scope are looked up
    # via the function's `__closure__` table. The latter is also the one that applies to
    # variables defined via the Python 3.12+ syntax since they desugar into annotation
    # scopes
    # (see https://docs.python.org/3/reference/compound_stmts.html#generic-functions).

    # First, we check if the variable is bound via the `__closure__` table. Those are
    # the ones that are mentioned in the `co_freevars` of the functions `__code__`.
    if f.__closure__ is not None:
        for i, x in enumerate(f.__code__.co_freevars):
            if x in generic_values:
                f.__closure__[i].cell_contents = generic_values.pop(x)

    # The remaining ones can be set via the `__globals__` table of the function. Note
    # that mutating `f.__globals__` also mutates the globals of other functions defined
    # in the same frame. Thus, we need to cache the old values so we can restore them
    # afterwards.
    old = {x: f.__globals__[x] for x in generic_values if x in f.__globals__}
    f.__globals__.update(generic_values)
    try:
        yield
    finally:
        for x in generic_values:
            if x not in old:
                del f.__globals__[x]
        f.__globals__.update(old)
