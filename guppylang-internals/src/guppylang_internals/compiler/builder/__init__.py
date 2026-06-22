from abc import ABC, abstractmethod, abstractproperty
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from types import TracebackType
from typing import Generic, NamedTuple, TypeAlias, TypeVar

from hugr import Node, Wire, val
from hugr import tys as ht
from hugr.build import Block, Case, Cfg, Conditional, TailLoop
from hugr.build import function as hf
from hugr.hugr.node_port import ToNode
from hugr.metadata import HugrDebugInfo
from hugr.ops import DataflowOp, Output
from typing_extensions import Self, override

from guppylang_internals.ast_util import AstNode
from guppylang_internals.metadata.debug_info_util import (
    debug_conditions_fulfilled,
    make_location_record,
)
from guppylang_internals.tys import Effect


@dataclass(frozen=True)
class Pure:
    op: DataflowOp


OpWithEffects: TypeAlias = Pure | tuple[DataflowOp, Iterable[Effect]]


@dataclass
class DFBuilder(ABC, ToNode):
    """A wrapper around a dataflow graph builder which ensures compiler-specific
    additional actions can be performed every time an operation is added to the graph.

    Manages attaching debug information, which requires keeping track of the most
    relevant AST node for each operation being compiled with `current_ast_node`,
    and also manages adding Order edges for side-effecting operations, including
    propagating side-effect-ness to parent builders (e.g. TailLoop, Conditional).
    """

    current_ast_node: AstNode | None = field(default=None, kw_only=True)
    _last_side_effect: dict[Effect, Node] = field(default_factory=dict, init=False)

    @abstractproperty
    def _raw(self) -> hf.Function | Case | TailLoop | Block:
        """The underlying Hugr dataflow graph builder."""

    @contextmanager
    def set_ast_context(self, ast_node: AstNode | None) -> Iterator[None]:
        """Context manager to set the current AST node context for debug information
        attachment - within the context of this manager the given `ast_node` will be
        considered the most relevant AST node for any operation added, temporarily
        overriding the previous `current_ast_node`.
        """
        prev_node = self.current_ast_node
        self.current_ast_node = ast_node
        try:
            yield
        finally:
            self.current_ast_node = prev_node

    def define_function(
        self, name: str, input_types: ht.TypeRow, output_types: ht.TypeRow
    ) -> "FunctionBuilder":
        return FunctionBuilder(
            self._raw.module_root_builder().define_function(
                name,
                input_types,
                output_types,
            )
        )

    def to_node(self) -> Node:
        return self._raw.to_node()

    @property
    def input_node(self) -> Node:
        return self._raw.input_node

    def inputs(self) -> Sequence[Wire]:
        return self._raw.inputs()

    def set_outputs(self, *outputs: Wire) -> hf.Function | Case | TailLoop | Block:
        self._raw.set_outputs(*outputs)
        self._handle_side_effects(
            self._raw.output_node, list(self._last_side_effect.keys())
        )
        return self._raw

    def add_op(
        self,
        op: OpWithEffects,
        /,
        *args: Wire,
        set_debug_info: bool = True,
    ) -> Node:
        """Adds an op to the dataflow graph builder. Set `set_debug_info=False` to
        avoid automatic debug information attachment.
        """
        op, effects = (op.op, []) if isinstance(op, Pure) else op
        op_node = self._raw.add_op(op, *args)
        self._handle_side_effects(op_node, effects)

        if set_debug_info and debug_conditions_fulfilled(self.current_ast_node):
            assert self.current_ast_node is not None  # for type-checker
            self._raw.hugr[op_node].metadata[HugrDebugInfo] = make_location_record(
                self.current_ast_node
            )
        return op_node

    def _handle_side_effects(self, op_node: ToNode, effects: Iterable[Effect]) -> None:
        """Updates Hugr to reflect `op_node` having effects `effects`.
        Does nothing if effects is empty (or the node already has those effects)."""
        node = op_node.to_node()
        to_propagate = set()  # Effects newly added to our container

        def get_last_node(e: Effect) -> Node:
            last = self._last_side_effect.get(e)
            if last is None:
                to_propagate.add(e)
                last = self.input_node
            else:
                assert not isinstance(self._raw.hugr[last].op, Output)
            self._last_side_effect[e] = node
            return last

        prev_nodes = {get_last_node(e) for e in effects}
        # Avoid cycles and duplicate edges:
        prev_nodes.discard(node)
        for prev in self._raw.hugr.incoming_order_links(node):
            prev_nodes.discard(prev)

        for prev in prev_nodes:
            self._raw.add_state_order(prev, node)

        if to_propagate:
            self._propagate_side_effects(to_propagate)

    @abstractmethod
    def _propagate_side_effects(self, effects: Iterable[Effect]) -> None:
        """Subclasses must implement to mark the container node
        as side-effecting within any parent/ancestor builder"""

    def call(
        self,
        func: ToNode,
        *args: Wire,
        effects: Iterable[Effect],
        instantiation: ht.FunctionType | None = None,
        type_args: Sequence[ht.TypeArg] | None = None,
        set_debug_info: bool = True,
    ) -> Node:
        """Calls a static function in the graph. Set `set_debug_info=False` to
        avoid automatic debug information attachment.
        """
        call = self._raw.call(
            func, *args, instantiation=instantiation, type_args=type_args
        )
        self._handle_side_effects(call, effects)
        if set_debug_info and debug_conditions_fulfilled(self.current_ast_node):
            assert self.current_ast_node is not None  # for type-checker
            self._raw.hugr[call].metadata[HugrDebugInfo] = make_location_record(
                self.current_ast_node
            )
        return call

    # Other frequently used operations for which we want to avoid having to use
    # `_raw` every time for convenience, even though we aren't setting any debug
    # information in them (yet).

    def get_wire_type(self, wire: Wire) -> ht.Type | None:
        return self._raw.hugr.port_type(wire.out_port())

    def add_conditional(self, cond_wire: Wire, *args: Wire) -> "CondBuilder":
        return CondBuilder(self._raw.add_conditional(cond_wire, *args), self)

    def add_cfg(self, *args: Wire) -> Cfg:
        return self._raw.add_cfg(*args)

    def add_tail_loop(
        self, just_inputs: Sequence[Wire], rest: Sequence[Wire]
    ) -> "TailLoopBuilder":
        return TailLoopBuilder(self._raw.add_tail_loop(just_inputs, rest), self)

    def load(
        self, const: ToNode | val.Value, const_parent: ToNode | None = None
    ) -> Node:
        return self._raw.load(const, const_parent)

    def load_function(
        self,
        func: ToNode,
        instantiation: ht.FunctionType | None = None,
        type_args: Sequence[ht.TypeArg] | None = None,
    ) -> Node:
        return self._raw.load_function(func, instantiation, type_args)

    def add_const(self, value: val.Value, parent: ToNode | None = None) -> Node:
        return self._raw.add_const(value, parent)


B = TypeVar("B", bound=hf.Function | Case | TailLoop | Block)


@dataclass
class _DFBuilderRaw(DFBuilder, Generic[B]):
    _raw_builder: B

    @property
    def _raw(self) -> B:
        return self._raw_builder


@dataclass
class TailLoopBuilder(_DFBuilderRaw[TailLoop]):
    parent: DFBuilder

    def set_loop_outputs(self, predicate: Wire, *outputs: Wire) -> None:
        self._raw.set_loop_outputs(predicate, *outputs)
        self._handle_side_effects(
            self._raw.output_node, list(self._last_side_effect.keys())
        )

    def _propagate_side_effects(self, effects: Iterable[Effect]) -> None:
        self.parent._handle_side_effects(self._raw, effects)


@dataclass
class FunctionBuilder(_DFBuilderRaw[hf.Function]):
    def _propagate_side_effects(self, effects: Iterable[Effect]) -> None:
        pass  # No parent

    @override
    def set_outputs(self, *outputs: Wire) -> hf.Function:
        super().set_outputs(*outputs)
        return self._raw


@dataclass
class CaseBuilder(_DFBuilderRaw[Case]):
    parent: Conditional
    grandparent: DFBuilder

    def _propagate_side_effects(self, effects: Iterable[Effect]) -> None:
        # No need to do anything in the Conditional,
        # but the Conditional itself needs to be ordered inside its parent
        self.grandparent._handle_side_effects(self.parent, effects)


@dataclass
class CondBuilder(ToNode):
    conditional: Conditional
    parent: DFBuilder

    def add_case(self, case_id: int) -> CaseBuilder:
        return CaseBuilder(
            self.conditional.add_case(case_id), self.conditional, self.parent
        )

    def to_node(self) -> Node:
        return self.conditional.to_node()

    def __enter__(self) -> Self:
        c = self.conditional.__enter__()
        assert c is self.conditional
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.conditional.__exit__(exc_type, exc_val, exc_tb)


@dataclass
class BlockBuilder(_DFBuilderRaw[Block]):
    parent: Cfg
    grandparent: DFBuilder

    def _propagate_side_effects(self, effects: Iterable[Effect]) -> None:
        # No need to do anything in the CFG, but the CFG itself
        # needs to be ordered inside its parent,
        self.grandparent._handle_side_effects(self.parent, effects)

    def set_block_outputs(self, branching: Wire, *other_outputs: Wire) -> None:
        self._raw.set_outputs(branching, *other_outputs)
        self._handle_side_effects(
            self._raw.output_node, list(self._last_side_effect.keys())
        )
