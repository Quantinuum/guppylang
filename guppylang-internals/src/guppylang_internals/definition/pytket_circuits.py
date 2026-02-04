import ast
from dataclasses import dataclass, field
from typing import Any, cast

import hugr.build.function as hf
from guppylang.defs import GuppyDefinition
from hugr import Node, Wire, envelope, ops, val
from hugr import tys as ht
from hugr.build.dfg import DefinitionBuilder, OpVar
from hugr.envelope import EnvelopeConfig
from hugr.std.float import FLOAT_T
from pytket.circuit import Circuit

from guppylang_internals.ast_util import AstNode, has_empty_body, with_loc
from guppylang_internals.checker.core import Context, Globals
from guppylang_internals.checker.errors.comptime_errors import PytketSignatureMismatch
from guppylang_internals.checker.expr_checker import check_call, synthesize_call
from guppylang_internals.checker.func_checker import (
    check_signature,
)
from guppylang_internals.compiler.core import CompilerContext, DFContainer
from guppylang_internals.definition.common import (
    CompilableDef,
    ParsableDef,
)
from guppylang_internals.definition.declaration import BodyNotEmptyError
from guppylang_internals.definition.function import (
    PyFunc,
    compile_call,
    load_with_args,
    parse_py_func,
)
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.definition.value import (
    CallableDef,
    CallReturnWires,
    CompiledCallableDef,
    CompiledHugrNodeDef,
)
from guppylang_internals.engine import ENGINE
from guppylang_internals.error import GuppyError, InternalGuppyError
from guppylang_internals.nodes import GlobalCall
from guppylang_internals.span import SourceMap, Span, ToSpan
from guppylang_internals.std._internal.compiler.array import (
    array_new,
    array_unpack,
)
from guppylang_internals.std._internal.compiler.quantum import from_halfturns_unchecked
from guppylang_internals.std._internal.compiler.tket_bool import OpaqueBool, make_opaque
from guppylang_internals.tys.builtin import array_type, bool_type, float_type
from guppylang_internals.tys.subst import Inst, Subst
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    Type,
    row_to_type,
)


@dataclass(frozen=True)
class RawPytketDef(ParsableDef):
    """A raw function stub definition describing the signature of a circuit.

    Args:
        id: The unique definition identifier.
        name: The name of the function stub.
        defined_at: The AST node where the stub was defined.
        python_func: The Python function stub.
        input_circuit: The user-provided pytket circuit.
    """

    python_func: PyFunc
    input_circuit: Any

    description: str = field(default="pytket circuit", init=False)

    def parse(self, globals: Globals, sources: SourceMap) -> "ParsedPytketDef":
        """Parses and checks the user-provided signature matches the user-provided
        circuit.
        """
        # Retrieve stub signature.
        func_ast, _ = parse_py_func(self.python_func, sources)
        if not has_empty_body(func_ast):
            # Function stub should have empty body.
            raise GuppyError(BodyNotEmptyError(func_ast.body[0], self.name))
        stub_signature = check_signature(func_ast, globals, self.id)

        # Compare signatures.
        circuit_signature = _signature_from_circuit(self.input_circuit, self.defined_at)
        if not (
            circuit_signature.inputs == stub_signature.inputs
            and circuit_signature.output == stub_signature.output
        ):
            err = PytketSignatureMismatch(func_ast, self.name)
            err.add_sub_diagnostic(
                PytketSignatureMismatch.TypeHint(None, circ_sig=circuit_signature)
            )
            raise GuppyError(err)
        return ParsedPytketDef(
            self.id, self.name, func_ast, stub_signature, self.input_circuit, False
        )


@dataclass(frozen=True)
class RawLoadPytketDef(ParsableDef):
    """A raw definition for loading pytket circuits without explicit function stub.

    Args:
        id: The unique definition identifier.
        name: The name of the circuit function.
        defined_at: The AST node of the definition (here always None).
        source_span: The source span where the circuit was loaded.
        input_circuit: The user-provided pytket circuit.
        use_arrays: Whether the circuit function should use arrays as input types.
    """

    source_span: Span | None
    input_circuit: Any
    use_arrays: bool

    description: str = field(default="pytket circuit", init=False)

    def parse(self, globals: Globals, sources: SourceMap) -> "ParsedPytketDef":
        """Creates a function signature based on the user-provided circuit."""
        circuit_signature = _signature_from_circuit(
            self.input_circuit, self.source_span, self.use_arrays
        )

        return ParsedPytketDef(
            self.id,
            self.name,
            self.defined_at,
            circuit_signature,
            self.input_circuit,
            self.use_arrays,
        )


@dataclass(frozen=True)
class ParsedPytketDef(CallableDef, CompilableDef):
    """A circuit definition with signature.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node of the function stub, if there is one.
        ty: The type of the function.
        input_circuit: The user-provided pytket circuit.
        use_arrays: Whether the circuit function should use arrays as input types.
    """

    ty: FunctionType
    input_circuit: Any
    use_arrays: bool

    description: str = field(default="pytket circuit", init=False)

    def compile_outer(
        self, module: DefinitionBuilder[OpVar], ctx: CompilerContext
    ) -> "CompiledPytketDef":
        """Adds a Hugr `FuncDefn` node for this function to the Hugr."""
        try:
            import pytket

            if isinstance(self.input_circuit, pytket.circuit.Circuit):
                from tket.circuit import (  # type: ignore[import-untyped, import-not-found, unused-ignore]
                    Tk2Circuit,
                )

                # TODO extract the correct entry point from the module
                circ = envelope.read_envelope(
                    Tk2Circuit(self.input_circuit).to_bytes(EnvelopeConfig.TEXT)
                ).modules[0]

                mapping = module.hugr.insert_hugr(circ)
                hugr_func = mapping[circ.entrypoint]

                func_type = self.ty.to_hugr_poly(ctx)
                outer_func = module.module_root_builder().define_function(
                    self.name, func_type.body.input, func_type.body.output
                )

                # Number of qubit inputs in the outer function.
                offset = (
                    len(self.input_circuit.q_registers)
                    if self.use_arrays
                    else self.input_circuit.n_qubits
                )

                input_list: list[Wire] = []
                if self.use_arrays:
                    # If the input is given as arrays, we need to unpack each element in
                    # them into separate wires.
                    for i, q_reg in enumerate(self.input_circuit.q_registers):
                        reg_wire = outer_func.inputs()[i]
                        elem_wires = outer_func.add_op(
                            array_unpack(ht.Qubit, q_reg.size), reg_wire
                        )
                        input_list.extend(elem_wires)

                else:
                    # Otherwise pass inputs directly.
                    input_list = list(outer_func.inputs()[:offset])

                # Initialise every input bit in the circuit as false.
                # TODO: Provide the option for the user to pass this input as well.
                bool_wires = [
                    outer_func.load(val.FALSE) for _ in range(self.input_circuit.n_bits)
                ]

                # Symbolic parameters (if present) get passed after qubits and bools.
                num_params = len(self.input_circuit.free_symbols())
                has_params = num_params != 0
                if has_params and "TKET1.input_parameters" not in hugr_func.metadata:
                    raise InternalGuppyError(
                        "Parameter metadata is missing from pytket circuit HUGR"
                    ) from None
                param_wires: list[Wire] = []
                # We assume they are given in lexicographic order by the user, then we
                # wire them up according to the metadata order.
                if has_params:
                    lex_params: list[Wire] = list(outer_func.inputs()[offset:])
                    if self.use_arrays:
                        unpack_result = outer_func.add_op(
                            array_unpack(
                                ht.Tuple(float_type().to_hugr(ctx)), num_params
                            ),
                            lex_params[0],
                        )
                        lex_params = list(unpack_result)
                    param_order = cast(
                        "list[str]", hugr_func.metadata["TKET1.input_parameters"]
                    )
                    lex_names = sorted(param_order)
                    name_to_param = dict(zip(lex_names, lex_params, strict=True))
                    angle_wires = [name_to_param[name] for name in param_order]
                    # Need to convert all angles to rotations.
                    for angle in angle_wires:
                        [halfturns] = outer_func.add_op(
                            ops.UnpackTuple([FLOAT_T]), angle
                        )
                        rotation = outer_func.add_op(
                            from_halfturns_unchecked(), halfturns
                        )
                        param_wires.append(rotation)

                # Pass all arguments to call node.
                call_node = outer_func.call(
                    hugr_func, *(input_list + bool_wires + param_wires)
                )

                # Pytket circuit hugr has qubit and bool wires in the opposite
                # order to Guppy output wires.
                output_list: list[Wire] = list(call_node.outputs())
                wires = (
                    output_list[self.input_circuit.n_qubits :]
                    + output_list[: self.input_circuit.n_qubits]
                )
                # Convert hugr sum bools into the opaque bools that Guppy uses.
                wires = [
                    outer_func.add_op(make_opaque(), wire)
                    if outer_func.hugr.port_type(wire.out_port()) == ht.Bool
                    else wire
                    for wire in wires
                ]

                if self.use_arrays:
                    array_wires: list[Wire] = []
                    wire_idx = 0
                    # First pack bool results into an array.
                    for c_reg in self.input_circuit.c_registers:
                        array_wires.append(
                            outer_func.add_op(
                                array_new(OpaqueBool, c_reg.size),
                                *wires[wire_idx : wire_idx + c_reg.size],
                            )
                        )
                        wire_idx = wire_idx + c_reg.size
                    # Then the borrowed qubits also need to be put back into arrays.
                    for q_reg in self.input_circuit.q_registers:
                        array_wires.append(
                            outer_func.add_op(
                                array_new(ht.Qubit, q_reg.size),
                                *wires[wire_idx : wire_idx + q_reg.size],
                            )
                        )
                        wire_idx = wire_idx + q_reg.size
                    wires = array_wires

                outer_func.set_outputs(*wires)

        except ImportError:
            pass

        return CompiledPytketDef(
            self.id,
            self.name,
            self.defined_at,
            self.ty,
            self.input_circuit,
            self.use_arrays,
            outer_func,
        )

    def check_call(
        self, args: list[ast.expr], ty: Type, node: AstNode, ctx: Context
    ) -> tuple[ast.expr, Subst]:
        """Checks the return type of a function call against a given type."""
        # Use default implementation from the expression checker
        args, subst, inst = check_call(self.ty, args, ty, node, ctx)
        node = with_loc(node, GlobalCall(def_id=self.id, args=args, type_args=inst))
        return node, subst

    def synthesize_call(
        self, args: list[ast.expr], node: AstNode, ctx: Context
    ) -> tuple[ast.expr, Type]:
        """Synthesizes the return type of a function call."""
        # Use default implementation from the expression checker
        args, ty, inst = synthesize_call(self.ty, args, node, ctx)
        node = with_loc(node, GlobalCall(def_id=self.id, args=args, type_args=inst))
        return node, ty


@dataclass(frozen=True)
class CompiledPytketDef(ParsedPytketDef, CompiledCallableDef, CompiledHugrNodeDef):
    """A function definition with a corresponding Hugr node.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was defined.
        ty: The type of the function.
        input_circuit: The user-provided pytket circuit.
        func_df: The Hugr function definition.
        use_arrays: Whether the circuit function uses arrays as input types.
    """

    func_def: hf.Function

    @property
    def hugr_node(self) -> Node:
        """The Hugr node this definition was compiled into."""
        return self.func_def.parent_node

    def load_with_args(
        self,
        type_args: Inst,
        dfg: DFContainer,
        ctx: CompilerContext,
        node: AstNode,
    ) -> Wire:
        """Loads the function as a value into a local Hugr dataflow graph."""
        # Use implementation from function definition.
        return load_with_args(type_args, dfg, self.ty, self.func_def)

    def compile_call(
        self,
        args: list[Wire],
        type_args: Inst,
        dfg: DFContainer,
        ctx: CompilerContext,
        node: AstNode,
    ) -> CallReturnWires:
        """Compiles a call to the function."""
        # Use implementation from function definition.
        return compile_call(args, type_args, dfg, self.ty, self.func_def)


def _signature_from_circuit(
    input_circuit: Circuit,
    defined_at: ToSpan | None,
    use_arrays: bool = False,
) -> FunctionType:
    """Helper function for inferring a function signature from a pytket circuit."""
    # May want to set proper unitary flags in the future.
    from guppylang.std.angles import angle  # Avoid circular imports
    from guppylang.std.quantum import qubit

    assert isinstance(qubit, GuppyDefinition)
    qubit_ty = cast("TypeDef", qubit.wrapped).check_instantiate([])

    angle_defn = ENGINE.get_checked(angle.id)  # type: ignore[attr-defined]
    assert isinstance(angle_defn, TypeDef)
    angle_ty = angle_defn.check_instantiate([])

    if use_arrays:
        inputs = [
            FuncInput(array_type(qubit_ty, q_reg.size), InputFlags.Inout)
            for q_reg in input_circuit.q_registers
        ]
        if len(input_circuit.free_symbols()) != 0:
            inputs.append(
                FuncInput(
                    array_type(angle_ty, len(input_circuit.free_symbols())),
                    InputFlags.NoFlags,
                )
            )
        outputs = [
            array_type(bool_type(), c_reg.size) for c_reg in input_circuit.c_registers
        ]
        circuit_signature = FunctionType(
            inputs,
            row_to_type(outputs),
        )
    else:
        param_inputs = [
            FuncInput(angle_ty, InputFlags.NoFlags)
            for _ in range(len(input_circuit.free_symbols()))
        ]
        circuit_signature = FunctionType(
            [FuncInput(qubit_ty, InputFlags.Inout)] * input_circuit.n_qubits
            + param_inputs,
            row_to_type([bool_type()] * input_circuit.n_bits),
        )
    return circuit_signature
