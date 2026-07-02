from hugr import Wire, ops
from hugr import tys as ht
from hugr.std.int import IntVal

from guppylang_internals.definition.custom import CustomInoutCallCompiler
from guppylang_internals.definition.gpu import (
    QSYSTEM_GPU_EXTENSION,
    ConstGpuModule,
    gpu_module_info,
)
from guppylang_internals.definition.value import CallReturnWires
from guppylang_internals.error import InternalGuppyError
from guppylang_internals.nodes import GlobalCall
from guppylang_internals.std._internal.compiler.arithmetic import convert_itousize
from guppylang_internals.std._internal.compiler.prelude import build_unwrap
from guppylang_internals.tys.ty import FunctionType


class GpuModuleInitCompiler(CustomInoutCallCompiler):
    """Compiler for initialising GPU modules. Calls "get_context" on the GPU extension
    and unwraps the `Option` result. Returns a `tket.gpu.context` wire."""

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        # Make a ConstGpuModule as a CustomConst
        assert len(args) == 0
        int_wire = self.builder.load(IntVal(0, width=6))
        ctx_wire = self.builder.add_op(convert_itousize(), int_wire)

        ctx_ty = QSYSTEM_GPU_EXTENSION.get_type("context").instantiate([])
        get_ctx_op = ops.ExtOp(
            QSYSTEM_GPU_EXTENSION.get_op("get_context"),
            ht.FunctionType([ht.USize()], [ht.Option(ctx_ty)]),
        )
        node = self.builder.add_op(get_ctx_op, ctx_wire)
        opt_w: Wire = node[0]
        err = "Failed to spawn GPU context"
        out_node = build_unwrap(self.builder, opt_w, err)
        return CallReturnWires(regular_returns=[out_node], inout_returns=[])


class GpuModuleDiscardCompiler(CustomInoutCallCompiler):
    """Compiler for discarding GPU contexts."""

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        assert len(args) == 1
        ctx = args[0]
        op = QSYSTEM_GPU_EXTENSION.get_op("dispose_context").instantiate([])
        self.builder.add_op(op, ctx)
        return CallReturnWires(regular_returns=[], inout_returns=[])


class GpuModuleCallCompiler(CustomInoutCallCompiler):
    """Compiler for GPU calls
    When a GPU method is called in guppy, we turn it into 3 hugr ops:
    * lookup: gpu.module -> gpu.func
    * call: gpu.context * gpu.func * inputs -> gpu.result
    * read_result: gpu.result -> gpu.context * outputs.

    For the gpu.module that we use in lookup, a constant is created for each
    call, using the gpu file information embedded in method's `self` argument.
    """

    fn_name: str
    fn_id: int | None

    def __init__(self, name: str, id_: int | None) -> None:
        self.fn_name = name
        self.fn_id = id_

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        # The arguments should be:
        # - a GPU context
        # - any args meant for the GPU function
        assert len(args) >= 1
        module_ty = QSYSTEM_GPU_EXTENSION.get_type("module").instantiate([])
        ctx_ty = QSYSTEM_GPU_EXTENSION.get_type("context").instantiate([])

        # Function type without Inout context arg (for building)
        assert isinstance(self.node, GlobalCall)
        assert self.func is not None
        gpu_sig = FunctionType(
            self.func.ty.inputs[1:],
            self.func.ty.output,
        ).to_hugr(self.ctx)

        inputs_row_arg = ht.ListArg([ty.type_arg() for ty in gpu_sig.input])
        output_row_arg = ht.ListArg([ty.type_arg() for ty in gpu_sig.output])

        func_ty = QSYSTEM_GPU_EXTENSION.get_type("func").instantiate(
            [inputs_row_arg, output_row_arg]
        )
        result_ty = QSYSTEM_GPU_EXTENSION.get_type("result").instantiate(
            [output_row_arg]
        )

        # Get the module information from the type
        selfarg = self.func.ty.inputs[0].ty
        if info := gpu_module_info(selfarg):
            const_module = self.builder.add_const(ConstGpuModule(*info))
        else:
            raise InternalGuppyError(
                "Expected cached signature to have GPU module as first arg"
            )

        gpu_module = self.builder.load(const_module)

        # Lookup the function we want
        if self.fn_id is None:
            fn_name_arg = ht.StringArg(self.fn_name)
            gpu_opdef = QSYSTEM_GPU_EXTENSION.get_op("lookup_by_name").instantiate(
                [fn_name_arg, inputs_row_arg, output_row_arg],
                ht.FunctionType([module_ty], [func_ty]),
            )
        else:
            fn_id_arg = ht.BoundedNatArg(self.fn_id)
            gpu_opdef = QSYSTEM_GPU_EXTENSION.get_op("lookup_by_id").instantiate(
                [fn_id_arg, inputs_row_arg, output_row_arg],
                ht.FunctionType([module_ty], [func_ty]),
            )
        gpu_func = self.builder.add_op(gpu_opdef, gpu_module)

        # Call the function
        call_op = QSYSTEM_GPU_EXTENSION.get_op("call").instantiate(
            [inputs_row_arg, output_row_arg],
            ht.FunctionType([ctx_ty, func_ty, *gpu_sig.input], [result_ty]),
        )

        result = self.builder.add_op(call_op, args[0], gpu_func, *args[1:])

        read_opdef = QSYSTEM_GPU_EXTENSION.get_op("read_result").instantiate(
            [output_row_arg],
            ht.FunctionType([result_ty], [ctx_ty, *gpu_sig.output]),
        )
        data = self.builder.add_op(read_opdef, result)  # ctx + return types
        match list(data[:]):
            case [ctx]:
                return CallReturnWires(regular_returns=[], inout_returns=[ctx])
            case [ctx, *values]:
                return CallReturnWires(regular_returns=[*values], inout_returns=[ctx])
            case _:
                raise InternalGuppyError("No outputs from tket.gpu.read_result.")
