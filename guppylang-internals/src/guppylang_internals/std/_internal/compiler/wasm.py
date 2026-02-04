from hugr import Wire, ops
from hugr import tys as ht

from guppylang_internals.definition.custom import CustomInoutCallCompiler
from guppylang_internals.definition.value import CallReturnWires
from guppylang_internals.error import InternalGuppyError
from guppylang_internals.nodes import GlobalCall
from guppylang_internals.std._internal.compiler.arithmetic import convert_itousize
from guppylang_internals.std._internal.compiler.prelude import build_unwrap
from guppylang_internals.std._internal.compiler.tket_exts import (
    WASM_EXTENSION,
    ConstWasmModule,
)
from guppylang_internals.tys.builtin import (
    wasm_module_name,
)
from guppylang_internals.tys.ty import (
    FunctionType,
)


class WasmModuleInitCompiler(CustomInoutCallCompiler):
    """Compiler for initialising WASM modules.
    Calls tket's "get_context" and unwraps the `Option` result.
    Returns a `tket.wasm.context` wire.
    """

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        # Make a ConstWasmModule as a CustomConst
        assert len(args) == 1
        ctx_arg = args[0]
        ctx_wire = self.builder.add_op(convert_itousize(), ctx_arg)

        ctx_ty = WASM_EXTENSION.get_type("context").instantiate([])
        get_ctx_op = ops.ExtOp(
            WASM_EXTENSION.get_op("get_context"),
            ht.FunctionType([ht.USize()], [ht.Option(ctx_ty)]),
        )
        node = self.builder.add_op(get_ctx_op, ctx_wire)
        opt_w: Wire = node[0]
        err = "Failed to spawn WASM context"
        out_node = build_unwrap(self.builder, opt_w, err)
        return CallReturnWires(regular_returns=[out_node], inout_returns=[])


class WasmModuleDiscardCompiler(CustomInoutCallCompiler):
    """Compiler for discarding WASM contexts."""

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        assert len(args) == 1
        ctx = args[0]
        op = WASM_EXTENSION.get_op("dispose_context").instantiate([])
        self.builder.add_op(op, ctx)
        return CallReturnWires(regular_returns=[], inout_returns=[])


class WasmModuleCallCompiler(CustomInoutCallCompiler):
    """Compiler for WASM calls
    When a wasm method is called in guppy, we turn it into 3 tket ops:
    * lookup: wasm.module -> wasm.func
    * call: wasm.context * wasm.func * inputs -> wasm.result
    * read_result: wasm.result -> wasm.context * outputs
    For the wasm.module that we use in lookup, a constant is created for each
    call, using the wasm file information embedded in method's `self` argument.
    """

    fn_name: str
    fn_id: int | None

    def __init__(self, name: str, id_: int | None) -> None:
        self.fn_name = name
        self.fn_id = id_

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        # The arguments should be:
        # - a WASM context
        # - any args meant for the WASM function
        assert len(args) >= 1
        module_ty = WASM_EXTENSION.get_type("module").instantiate([])
        ctx_ty = WASM_EXTENSION.get_type("context").instantiate([])

        fn_name_arg = ht.StringArg(self.fn_name)
        # Function type without Inout context arg (for building)
        assert isinstance(self.node, GlobalCall)
        assert self.func is not None
        wasm_sig = FunctionType(
            self.func.ty.inputs[1:],
            self.func.ty.output,
        ).to_hugr(self.ctx)

        inputs_row_arg = ht.ListArg([ty.type_arg() for ty in wasm_sig.input])
        output_row_arg = ht.ListArg([ty.type_arg() for ty in wasm_sig.output])

        func_ty = WASM_EXTENSION.get_type("func").instantiate(
            [inputs_row_arg, output_row_arg]
        )
        result_ty = WASM_EXTENSION.get_type("result").instantiate([output_row_arg])

        # Get the WASM module information from the type
        selfarg = self.func.ty.inputs[0].ty
        info = wasm_module_name(selfarg)
        if info is not None:
            const_module = self.builder.add_const(ConstWasmModule(info))
        else:
            raise InternalGuppyError(
                "Expected cached signature to have WASM module as first arg"
            )

        wasm_module = self.builder.load(const_module)

        # Lookup the function we want
        if self.fn_id is None:
            fn_name_arg = ht.StringArg(self.fn_name)
            wasm_opdef = WASM_EXTENSION.get_op("lookup_by_name").instantiate(
                [fn_name_arg, inputs_row_arg, output_row_arg],
                ht.FunctionType([module_ty], [func_ty]),
            )
        else:
            fn_id_arg = ht.BoundedNatArg(self.fn_id)
            wasm_opdef = WASM_EXTENSION.get_op("lookup_by_id").instantiate(
                [fn_id_arg, inputs_row_arg, output_row_arg],
                ht.FunctionType([module_ty], [func_ty]),
            )

        wasm_func = self.builder.add_op(wasm_opdef, wasm_module)

        # Call the function
        call_op = WASM_EXTENSION.get_op("call").instantiate(
            [inputs_row_arg, output_row_arg],
            ht.FunctionType([ctx_ty, func_ty, *wasm_sig.input], [result_ty]),
        )

        result = self.builder.add_op(call_op, args[0], wasm_func, *args[1:])

        read_opdef = WASM_EXTENSION.get_op("read_result").instantiate(
            [output_row_arg],
            ht.FunctionType([result_ty], [ctx_ty, *wasm_sig.output]),
        )
        data = self.builder.add_op(read_opdef, result)
        match list(data[:]):
            case [ctx]:
                return CallReturnWires(regular_returns=[], inout_returns=[ctx])
            case [ctx, *values]:
                return CallReturnWires(regular_returns=[*values], inout_returns=[ctx])
            case _:
                raise AssertionError("impossible")
