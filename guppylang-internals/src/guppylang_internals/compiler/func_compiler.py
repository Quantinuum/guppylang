from typing import TYPE_CHECKING

from hugr import Wire
from hugr import tys as ht
from hugr.build.function import Function

from guppylang_internals.compiler.cfg_compiler import compile_cfg
from guppylang_internals.compiler.core import CompilerContext, DFContainer
from guppylang_internals.compiler.hugr_extension import PartialOp
from guppylang_internals.nodes import CheckedNestedFunctionDef

if TYPE_CHECKING:
    from guppylang_internals.definition.function import CheckedFunctionDef


def compile_global_func_def(
    func: "CheckedFunctionDef",
    builder: Function,
    ctx: CompilerContext,
) -> None:
    """Compiles a top-level function definition to Hugr."""
    cfg = compile_cfg(func.cfg, builder, builder.inputs(), ctx)
    builder.set_outputs(*cfg)


def compile_local_func_def(
    func: CheckedNestedFunctionDef,
    dfg: DFContainer,
    ctx: CompilerContext,
) -> Wire:
    """Compiles a local (nested) function definition to Hugr and loads it into a value.

    Returns the wire output of the `LoadFunc` operation.
    """
    assert func.ty.input_names is not None

    # Pick an order for the captured variables
    captured = list(func.captured.values())
    captured_types = [v.ty.to_hugr(ctx) for v, _ in captured]

    # Whether the function calls itself recursively.
    recursive = func.name in func.cfg.live_before[func.cfg.entry_bb]

    # Prepend captured variables to the function arguments
    func_ty = func.ty.to_hugr(ctx)
    closure_ty = ht.FunctionType([*captured_types, *func_ty.input], func_ty.output)
    func_builder = dfg.builder.module_root_builder().define_function(
        func.name, closure_ty.input, closure_ty.output
    )

    # Nested functions are not generic, so no need to worry about monomorphization
    mono_args = ()

    # If we have captured variables and the body contains a recursive occurrence of
    # the function itself, then we provide the partially applied function as a local
    # variable
    call_args: list[Wire] = list(func_builder.inputs())
    if len(captured) > 0 and recursive:
        loaded = func_builder.load_function(func_builder, closure_ty)
        partial = func_builder.add_op(
            PartialOp.from_closure(closure_ty, captured_types),
            loaded,
            *func_builder.input_node[: len(captured)],
        )

        call_args.append(partial)
        func.cfg.input_tys.append(func.ty)

        # Compile the CFG
        cfg = compile_cfg(func.cfg, func_builder, call_args, ctx)
        func_builder.set_outputs(*cfg)
    else:
        # Otherwise, we treat the function like a normal global variable
        from guppylang_internals.definition.function import CompiledFunctionDef

        ctx.compiled[func.def_id, mono_args] = CompiledFunctionDef(
            func.def_id,
            func.name,
            func,
            mono_args,
            func.ty,
            None,
            func.cfg,
            func_builder,
        )
        ctx.worklist[func.def_id, mono_args] = None  # will compile the CFG later

    # Finally, load the function into the local data-flow graph
    loaded = dfg.builder.load_function(func_builder, closure_ty)
    if len(captured) > 0:
        loaded = dfg.builder.add_op(
            PartialOp.from_closure(closure_ty, captured_types),
            loaded,
            *(dfg[v] for v, _ in captured),
        )

    return loaded
