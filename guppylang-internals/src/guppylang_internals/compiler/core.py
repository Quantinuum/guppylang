import itertools
from abc import ABC
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, cast

import tket_exts
from hugr import Hugr, Node, Wire, ops
from hugr import ext as he
from hugr import tys as ht
from hugr.build import function as hf
from hugr.build.dfg import DP, DefinitionBuilder, DfBase
from hugr.hugr.base import OpVarCov
from hugr.hugr.node_port import ToNode
from hugr.std import PRELUDE
from hugr.std.collections.array import EXTENSION as ARRAY_EXTENSION
from hugr.std.collections.borrow_array import EXTENSION as BORROW_ARRAY_EXTENSION
from typing_extensions import assert_never

from guppylang_internals.checker.core import (
    FieldAccess,
    Globals,
    Place,
    PlaceId,
    TupleAccess,
    Variable,
)
from guppylang_internals.definition.common import (
    CheckedDef,
    CompilableDef,
    CompiledDef,
    DefId,
    Definition,
    MonomorphizableDef,
    RawDef,
)
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.definition.value import CompiledCallableDef
from guppylang_internals.diagnostic import Error
from guppylang_internals.engine import DEF_STORE, ENGINE
from guppylang_internals.error import GuppyError, InternalGuppyError
from guppylang_internals.std._internal.compiler.tket_exts import GUPPY_EXTENSION
from guppylang_internals.tys.arg import ConstArg, TypeArg
from guppylang_internals.tys.builtin import nat_type
from guppylang_internals.tys.common import ToHugrContext
from guppylang_internals.tys.const import BoundConstVar, ConstValue
from guppylang_internals.tys.param import ConstParam, Parameter
from guppylang_internals.tys.subst import Inst, Instantiator
from guppylang_internals.tys.ty import (
    BoundTypeVar,
    NumericType,
    StructType,
    TupleType,
    Type,
)

if TYPE_CHECKING:
    from guppylang_internals.tys.arg import Argument

CompiledLocals = dict[PlaceId, Wire]

#: Partial instantiation of generic type parameters for monomorphization.
#:
#: When compiling polymorphic definitions to Hugr, some of their generic parameters will
#: need to be monomorphized (e.g. to support language features that cannot be encoded
#: in Hugr, see `requires_monomorphization` for details). However, other generic
#: parameters can be faithfully captured in Hugr. Thus, we want to perform a *partial*
#: monomorphization when compiling to Hugr.
#:
#: A `mono_args: PartiallyMonomorphizedArgs` represents such a partial monomorphization
#: of generic parameters as a sequence of `Argument | None`. Concretely,
#: `mono_args[i] == None` means that the argument with index `i` is left as a
#: polymorphic Hugr type parameter, i.e. it is not monomorphised by Guppy. Otherwise,
#: `mono_args[i]` specifies the monomorphic instantiation  for parameter `i`. For
#: example, a function with 3 generic parameters that should all be retained in Hugr
#: will have mono_args = `(None, None, None)`.
#:
#: Finally, note that this sequence is required to be a tuple to ensure hashability.
PartiallyMonomorphizedArgs = tuple["Argument | None", ...]


@dataclass(frozen=True)
class GlobalConstId:
    id: int
    base_name: str

    _fresh_ids = itertools.count()

    @staticmethod
    def fresh(base_name: str) -> "GlobalConstId":
        return GlobalConstId(next(GlobalConstId._fresh_ids), base_name)

    @property
    def name(self) -> str:
        return f"{self.base_name}.{self.id}"


#: Unique identifier for a partially monomorphized definition.
#:
#: If the `DefId` corresponds to a `MonomorphizableDef`, then the second tuple entry
#: should hold the corresponding partial monomorphization. Otherwise, the second entry
#: should be `None`.
#:
#: Note the following subtlety: Functions are instances of `MonomorphizableDef`, even if
#: they aren't actually generic! This means that for non-generic function definitions we
#: will have an empty tuple `()` as `PartiallyMonomorphizedArgs`, but never `None`.
#: `None` only shows up for kinds of definitions that are never monomorphized (e.g.
#: definitions of constants).
MonoDefId = tuple[DefId, PartiallyMonomorphizedArgs | None]

#: Unique identifier for global Hugr constants and functions, the latter with optional
#: monomorphized type arguments
MonoGlobalConstId = tuple[GlobalConstId, PartiallyMonomorphizedArgs | None]


@dataclass(frozen=True)
class EntryMonomorphizeError(Error):
    title: ClassVar[str] = "Invalid entry point"
    span_label: ClassVar[str] = (
        "Function `{name}` is not a valid compilation entry point since the value of "
        "generic parameter `{param}` is not known"
    )
    name: str
    param: Parameter


class CompilerContext(ToHugrContext):
    """Compilation context containing all available definitions.

    Maintains a `worklist` of definitions which have been used by other compiled code
    (i.e. `compile_outer` has been called) but have not yet been compiled/lowered
    themselves (i.e. `compile_inner` has not yet been called).
    """

    module: DefinitionBuilder[ops.Module]

    #: The definitions compiled so far. For `MonomorphizableDef`s, their id can occur
    #: multiple times here with respectively different partial monomorphizations. See
    #: `MonoDefId` and `PartiallyMonomorphizedArgs` for details.
    compiled: dict[MonoDefId, CompiledDef]

    # use dict over set for deterministic iteration order
    worklist: dict[MonoDefId, None]

    global_funcs: dict[MonoGlobalConstId, hf.Function]

    #: Partial instantiation for some of the type parameters of the current function for
    #: the purpose of monomorphization
    current_mono_args: PartiallyMonomorphizedArgs | None

    checked_globals: Globals

    def __init__(
        self,
        module: DefinitionBuilder[ops.Module],
    ) -> None:
        self.module = module
        self.worklist = {}
        self.compiled = {}
        self.global_funcs = {}
        self.checked_globals = Globals(None)
        self.current_mono_args = None

    @contextmanager
    def set_monomorphized_args(
        self, mono_args: PartiallyMonomorphizedArgs | None
    ) -> Iterator[None]:
        """Context manager to set the partial monomorphization for the function that is
        compiled currently being compiled.
        """
        old = self.current_mono_args
        self.current_mono_args = mono_args
        yield
        self.current_mono_args = old

    def build_compiled_def(
        self, def_id: DefId, type_args: Inst
    ) -> tuple[CompiledDef, Inst]:
        """Returns the compiled definitions corresponding to the given ID, along with
        the remaining type args that have not been monomorphized away.

        Might mutate the current Hugr if this definition has never been compiled before.
        """
        # TODO: The check below is a hack to support nested function definitions. We
        #  forgot to insert frames for nested functions into the DEF_STORE, which would
        #  make the call to `ENGINE.get_checked` below fail. For now, let's just short-
        #  cut if the function doesn't take any generic params (as is the case for all
        #  nested functions).
        #  See https://github.com/quantinuum/guppylang/issues/1032
        if (def_id, ()) in self.compiled:
            assert type_args == []
            return self.compiled[def_id, ()], type_args

        mono_args: PartiallyMonomorphizedArgs | None = None
        rem_args = type_args
        compile_outer: Callable[[], CompiledDef]
        match ENGINE.get_checked(def_id):
            case MonomorphizableDef(params=params) as monomorphizable:
                mono_args, rem_args = partially_monomorphize_args(
                    params, type_args, self
                )
                compile_outer = lambda: monomorphizable.monomorphize(  # noqa: E731 (assign-lambda)
                    self.module, mono_args, self, get_parent_type(monomorphizable)
                )
            case CompilableDef() as compilable:
                compile_outer = lambda: compilable.compile_outer(self.module, self)  # noqa: E731
            case CompiledDef() as compiled_defn:
                compile_outer = lambda: compiled_defn  # noqa: E731
            case defn:
                compile_outer = assert_never(defn)
        if (def_id, mono_args) not in self.compiled:
            self.compiled[def_id, mono_args] = compile_outer()
            self.worklist[def_id, mono_args] = None
        return self.compiled[def_id, mono_args], rem_args

    def compile(self, defn: CheckedDef) -> CompiledDef:
        """Compiles the given definition and all of its dependencies into the current
        Hugr."""
        # Check and compile the entry point
        entry_mono_args: PartiallyMonomorphizedArgs | None = None
        entry_compiled: CompiledDef
        match ENGINE.get_checked(defn.id):
            case MonomorphizableDef(params=params) as defn:
                # Entry point is not allowed to require monomorphization
                if mono_params := require_monomorphization(params):
                    mono_param = mono_params.pop()
                    err = EntryMonomorphizeError(defn.defined_at, defn.name, mono_param)
                    raise GuppyError(err)
                # Thus, the partial monomorphization for the entry point is always empty
                entry_mono_args = tuple(None for _ in params)
                entry_compiled = defn.monomorphize(
                    self.module, entry_mono_args, self, get_parent_type(defn)
                )
            case CompilableDef() as defn:
                entry_compiled = defn.compile_outer(self.module, self)
            case CompiledDef() as defn:
                entry_compiled = defn
            case defn:
                entry_compiled = assert_never(defn)

        self.compiled[defn.id, entry_mono_args] = entry_compiled
        self.worklist[defn.id, entry_mono_args] = None

        # Compile definition bodies
        while self.worklist:
            next_id, mono_args = self.worklist.popitem()[0]
            next_def = self.compiled[next_id, mono_args]
            with track_hugr_side_effects(), self.set_monomorphized_args(mono_args):
                next_def.compile_inner(self)

        # Insert explicit drops for affine types
        # TODO: This is a quick workaround until we can properly insert these drops
        # during linearity checking. See https://github.com/quantinuum/guppylang/issues/1082
        insert_drops(self.module.hugr)

        return entry_compiled

    def build_compiled_instance_func(
        self,
        ty: Type | TypeDef,
        name: str,
        type_args: Inst,
    ) -> tuple[CompiledCallableDef, Inst] | None:
        """Returns s compiled instance method along with its remaining type args that
        have not been monomorphized away, or `None` if the type doesn't have a matching
        method.

        Compiles the definition and all of its dependencies into the current Hugr.
        """
        from guppylang_internals.engine import ENGINE

        parsed_func = self.checked_globals.get_instance_func(ty, name)
        if parsed_func is None:
            return None
        checked_func = ENGINE.get_checked(parsed_func.id)
        compiled_func, rem_args = self.build_compiled_def(checked_func.id, type_args)
        assert isinstance(compiled_func, CompiledCallableDef)
        return compiled_func, rem_args

    def declare_global_func(
        self,
        const_id: GlobalConstId,
        func_ty: ht.PolyFuncType,
        mono_args: PartiallyMonomorphizedArgs | None = None,
    ) -> tuple[hf.Function, bool]:
        """
        Creates a function builder for a global function if it doesn't already exist,
        else returns the existing one.
        """
        if (const_id, mono_args) in self.global_funcs:
            return self.global_funcs[const_id, mono_args], True
        func = self.module.module_root_builder().define_function(
            name=const_id.name,
            input_types=func_ty.body.input,
            output_types=func_ty.body.output,
            type_params=func_ty.params,
        )
        self.global_funcs[const_id, mono_args] = func
        return func, False

    def type_var_to_hugr(self, var: BoundTypeVar) -> ht.Type:
        """Compiles a bound Guppy type variable into a Hugr type.

        Takes care of performing partial monomorphization as specified in the current
        context.
        """
        if self.current_mono_args is None:
            # If we're not inside a monomorphized context, just return the Hugr
            # variable with the same de Bruijn index
            return ht.Variable(var.idx, var.hugr_bound)

        match self.current_mono_args[var.idx]:
            # Either we have a decided to monomorphize the corresponding parameter...
            case TypeArg(ty=ty):
                return ty.to_hugr(self)
            # ... or we're still want to be generic in Hugr
            case None:
                # But in that case we'll have to down-shift the de Bruijn index to
                # account for earlier params that have been monomorphized away
                hugr_idx = compile_variable_idx(var.idx, self.current_mono_args)
                return ht.Variable(hugr_idx, var.hugr_bound)
            case _:
                raise InternalGuppyError("Invalid monomorphization")

    def const_var_to_hugr(self, var: BoundConstVar) -> ht.TypeArg:
        """Compiles a bound Guppy constant variable into a Hugr type argument.

        Takes care of performing partial monomorphization as specified in the current
        context.
        """
        if var.ty != nat_type():
            raise InternalGuppyError(
                "Tried to convert non-nat const type argument to Hugr. This should "
                "have been monomprhized away."
            )
        param = ht.BoundedNatParam(upper_bound=None)

        if self.current_mono_args is None:
            # If we're not inside a monomorphized context, just return the Hugr
            # variable with the same de Bruijn index
            return ht.VariableArg(var.idx, param)

        match self.current_mono_args[var.idx]:
            # Either we have a decided to monomorphize the corresponding parameter...
            case ConstArg(const=ConstValue(value=int(v))):
                return ht.BoundedNatArg(n=v)
            # ... or we're still want to be generic in Hugr
            case None:
                # But in that case we'll have to down-shift the de Bruijn index to
                # account for earlier params that have been monomorphized away
                hugr_idx = compile_variable_idx(var.idx, self.current_mono_args)
                return ht.VariableArg(hugr_idx, param)
            case _:
                raise InternalGuppyError("Invalid monomorphization")


@dataclass
class DFContainer:
    """A dataflow graph under construction.

    This class is passed through the entire compilation pipeline and stores a builder
    for the dataflow child-graph currently being constructed as well as all live local
    variables. Note that the variable map is mutated in-place and always reflects the
    current compilation state.
    """

    builder: DfBase[ops.DfParentOp]
    ctx: CompilerContext
    locals: CompiledLocals = field(default_factory=dict)

    def __init__(
        self,
        builder: DfBase[DP],
        ctx: CompilerContext,
        locals: CompiledLocals | None = None,
    ) -> None:
        generic_builder = cast("DfBase[ops.DfParentOp]", builder)
        if locals is None:
            locals = {}
        self.builder = generic_builder
        self.ctx = ctx
        self.locals = locals

    def __getitem__(self, place: Place) -> Wire:
        """Constructs a wire for a local place in this DFG.

        Note that this mutates the Hugr since we might need to pack or unpack some
        tuples to obtain a port for places that involve struct fields.
        """
        # First check, if we already have a wire for this place
        if place.id in self.locals:
            return self.locals[place.id]
        # Otherwise, our only hope is that it's a struct or tuple value that we can
        # rebuild by packing the wires of its constituting fields
        elif isinstance(place.ty, StructType):
            children: list[Place] = [
                FieldAccess(place, field, None) for field in place.ty.fields
            ]
        elif isinstance(place.ty, TupleType):
            children = [
                TupleAccess(place, elem, idx, None)
                for idx, elem in enumerate(place.ty.element_types)
            ]
        else:
            raise InternalGuppyError(f"Couldn't obtain a port for `{place}`")
        child_types = [child.ty.to_hugr(self.ctx) for child in children]
        child_wires = [self[child] for child in children]
        wire = self.builder.add_op(ops.MakeTuple(child_types), *child_wires)[0]
        for child in children:
            if child.ty.linear:
                self.locals.pop(child.id)
        self.locals[place.id] = wire
        return wire

    def __setitem__(self, place: Place, port: Wire) -> None:
        # When assigning a struct value, we immediately unpack it recursively and only
        # store the leaf wires.
        is_return = isinstance(place, Variable) and is_return_var(place.name)
        if isinstance(place.ty, StructType) and not is_return:
            unpack = self.builder.add_op(
                ops.UnpackTuple([t.ty.to_hugr(self.ctx) for t in place.ty.fields]), port
            )
            for field, field_port in zip(place.ty.fields, unpack, strict=True):
                self[FieldAccess(place, field, None)] = field_port
            # If we had a previous wire assigned to this place, we need forget about it.
            # Otherwise, we might use this old value when looking up the place later
            self.locals.pop(place.id, None)
        # Same for tuples.
        elif isinstance(place.ty, TupleType) and not is_return:
            hugr_elem_tys = [ty.to_hugr(self.ctx) for ty in place.ty.element_types]
            unpack = self.builder.add_op(ops.UnpackTuple(hugr_elem_tys), port)
            for idx, (elem, elem_port) in enumerate(
                zip(place.ty.element_types, unpack, strict=True)
            ):
                self[TupleAccess(place, elem, idx, None)] = elem_port
            self.locals.pop(place.id, None)
        else:
            self.locals[place.id] = port

    def __contains__(self, place: Place) -> bool:
        return place.id in self.locals

    def __copy__(self) -> "DFContainer":
        # Make a copy of the var map so that mutating the copy doesn't
        # mutate our variable mapping
        return DFContainer(self.builder, self.ctx, self.locals.copy())


class CompilerBase(ABC):
    """Base class for the Guppy compiler."""

    ctx: CompilerContext

    def __init__(self, ctx: CompilerContext) -> None:
        self.ctx = ctx


def return_var(n: int) -> str:
    """Name of the dummy variable for the n-th return value of a function.

    During compilation, we treat return statements like assignments of dummy variables.
    For example, the statement `return e0, e1, e2` is treated like `%ret0 = e0 ; %ret1 =
    e1 ; %ret2 = e2`. This way, we can reuse our existing mechanism for passing of live
    variables between basic blocks."""
    return f"%ret{n}"


def is_return_var(x: str) -> bool:
    """Checks whether the given name is a dummy return variable."""
    return x.startswith("%ret")


def get_parent_type(defn: Definition) -> "RawDef | None":
    """Returns the RawDef registered as the parent of `child` in the DEF_STORE,
    or None if it has no parent."""
    if parent_ty_id := DEF_STORE.impl_parents.get(defn.id):
        return DEF_STORE.raw_defs[parent_ty_id]
    else:
        return None


def require_monomorphization(params: Sequence[Parameter]) -> set[Parameter]:
    """Returns the subset of type parameters that must be monomorphized before compiling
    to Hugr.

    This is required for some Guppy language features that cannot be encoded in Hugr
    yet. Currently, this applies to:
    * non-nat const parameters
    * parameters that occur in the type of const parameters
    """
    mono_params: set[Parameter] = set()
    for param in params:
        match param:
            case ConstParam(ty=ty) if ty != NumericType(NumericType.Kind.Nat):
                mono_params.add(param)
                # If the constant type refers to any bound variables, then those will
                # need to be monomorphized as well
                for var in ty.bound_vars:
                    mono_params.add(params[var.idx])
            case _:
                pass
    return mono_params


def partially_monomorphize_args(
    params: Sequence[Parameter],
    args: Inst,
    ctx: CompilerContext,
) -> tuple[PartiallyMonomorphizedArgs, Inst]:
    """
    Given an instantiation of all type parameters, extracts the ones that will need to
    be monomorphized.

    Also takes care of normalising bound variables w.r.t. the current monomorphization.
    """
    # Normalise args w.r.t. the current outer monomorphisation
    if ctx.current_mono_args is not None:
        instantiator = Instantiator(ctx.current_mono_args, allow_partial=True)
        args = [arg.transform(instantiator) for arg in args]

    # Filter args depending on whether they need monomorphization or not. For this, we
    # can't purely rely on the `require_monomorphization` function above since the
    # instantiation also needs to be taken into account. For example, consider
    # a function `def foo[T, x: T](...)`. Normally, both parameters would need to be
    # monomorphized. However, if we instantiate `T := nat`, suddenly `x` no longer needs
    # be monomorphized since we can use bounded nats in Hugr. Thus, we have to replicate
    # the behaviour of `require_monomorphization` while taking `args` into account.
    mono_args: list[Argument | None] = [None] * len(args)
    for param, arg in zip(params, args, strict=True):
        match param, param.instantiate_bounds(args):
            case ConstParam(ty=original_ty), ConstParam(ty=inst_ty):
                # If the original const type is not `nat`, then all variables occurring
                # in the type need to be monomorphised
                if original_ty != nat_type():
                    for var in original_ty.bound_vars:
                        mono_args[var.idx] = args[var.idx]
                # If the const type is still not `nat` after normalisation, then the
                # const arg itself also needs to be monomorphized
                if inst_ty != nat_type():
                    mono_args[param.idx] = arg

    # Mono-arguments should not refer to any bound variables
    assert all(mono_arg is None or not mono_arg.bound_vars for mono_arg in mono_args)

    rem_args = [arg for i, arg in enumerate(args) if mono_args[i] is None]
    return tuple(mono_args), rem_args


def compile_variable_idx(idx: int, mono_args: PartiallyMonomorphizedArgs) -> int:
    """Returns the Hugr index for a variable.

    Takes care of shifting down Guppy's indices to account for the current partial
    monomorphization. This avoids gaps in Hugr indices due to the fact that not all
    Guppy parameters are lowered to Hugr (some are monomorphized away).
    """
    assert mono_args[idx] is None, "Should not compile monomorphized index"
    return sum(1 for arg in mono_args[:idx] if arg is None)


QUANTUM_EXTENSION = tket_exts.quantum()
RESULT_EXTENSION = tket_exts.result()
DEBUG_EXTENSION = tket_exts.debug()

#: List of extension ops that have side-effects, identified by their qualified name
EXTENSION_OPS_WITH_SIDE_EFFECTS: list[str] = [
    # Results should be order w.r.t. each other but also w.r.t. panics
    *(op_def.qualified_name() for op_def in RESULT_EXTENSION.operations.values()),
    PRELUDE.get_op("panic").qualified_name(),
    PRELUDE.get_op("exit").qualified_name(),
    DEBUG_EXTENSION.get_op("StateResult").qualified_name(),
    # Qubit allocation and deallocation have the side-effect of changing the number of
    # available free qubits
    QUANTUM_EXTENSION.get_op("QAlloc").qualified_name(),
    QUANTUM_EXTENSION.get_op("QFree").qualified_name(),
    QUANTUM_EXTENSION.get_op("MeasureFree").qualified_name(),
]


def may_have_side_effect(op: ops.Op) -> bool:
    """Checks whether an operation could have a side-effect.

    We need to insert implicit state order edges between these kinds of nodes to ensure
    they are executed in the correct order, even if there is no data dependency.
    """
    match op:
        case ops.ExtOp() as ext_op:
            return ext_op.op_def().qualified_name() in EXTENSION_OPS_WITH_SIDE_EFFECTS
        case ops.Custom(op_name=op_name, extension=extension):
            qualified_name = f"{extension}.{op_name}" if extension else op_name
            return qualified_name in EXTENSION_OPS_WITH_SIDE_EFFECTS
        case ops.Call() | ops.CallIndirect():
            # Conservative choice is to assume that all calls could have side effects.
            # In the future we could inspect the call graph to figure out a more
            # precise answer
            return True
        case _:
            # There is no need to handle TailLoop (in case of non-termination) since
            # TailLoops are only generated for array comprehensions which must have
            # statically-guaranteed (finite) size. TODO revisit this for lists.
            return False


@contextmanager
def track_hugr_side_effects() -> Iterator[None]:
    """Initialises the tracking of nodes with side-effects during Hugr building.

    Ensures that state-order edges are implicitly inserted between side-effectful nodes
    to ensure they are executed in the order they are added.
    """
    # Remember original `Hugr.add_node` method that is monkey-patched below.
    hugr_add_node = Hugr.add_node
    # Last node with potential side effects for each dataflow parent
    prev_node_with_side_effect: dict[Node, tuple[Node, Hugr[Any]]] = {}

    def hugr_add_node_with_order(
        self: Hugr[OpVarCov],
        op: ops.Op,
        parent: ToNode | None = None,
        num_outs: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Node:
        """Monkey-patched version of `Hugr.add_node` that takes care of implicitly
        inserting state order edges between operations that could have side-effects.
        """
        new_node = hugr_add_node(self, op, parent, num_outs, metadata)
        if may_have_side_effect(op):
            handle_side_effect(new_node, self)
        return new_node

    def handle_side_effect(node: Node, hugr: Hugr[OpVarCov]) -> None:
        """Performs the actual order-edge insertion, assuming that `node` has a side-
        effect."""
        parent = hugr[node].parent
        assert parent is not None

        if prev := prev_node_with_side_effect.get(parent):
            prev_node = prev[0]
        else:
            # This is the first side-effectful op in this DFG. Recurse on the parent
            # since the parent is also considered side-effectful now. We shouldn't walk
            # up through function definitions (only the Module is above)
            if not isinstance(hugr[parent].op, ops.FuncDefn):
                handle_side_effect(parent, hugr)
                # For DataflowBlocks and Cases, recurse to mark their containing CFG
                # or Conditional as side-effectful as well, but there is nothing to do
                # locally: we cannot add order edges, but Conditional/CFG semantics
                # ensure execution if appropriate.
                if isinstance(hugr[parent].op, ops.Conditional | ops.CFG):
                    return
            prev_node = hugr.children(parent)[0]
            assert isinstance(hugr[prev_node].op, ops.Input)

        # Add edge, but avoid self-loops for containers when recursing up the hierarchy.
        if prev_node != node:
            hugr.add_order_link(prev_node, node)
            prev_node_with_side_effect[parent] = (node, hugr)

    # Monkey-patch the `add_node` method
    Hugr.add_node = hugr_add_node_with_order  # type: ignore[method-assign]
    try:
        yield
        for parent, (last, hugr) in prev_node_with_side_effect.items():
            # Connect the last side-effecting node to Output
            outp = hugr.children(parent)[1]
            assert isinstance(hugr[outp].op, ops.Output)
            assert last != outp
            hugr.add_order_link(last, outp)
    finally:
        Hugr.add_node = hugr_add_node  # type: ignore[method-assign]


def qualified_name(type_def: he.TypeDef) -> str:
    """Returns the qualified name of a Hugr extension type.
    TODO: Remove once upstreamed, see https://github.com/quantinuum/hugr/issues/2426
    """
    if type_def._extension is not None:
        return f"{type_def._extension.name}.{type_def.name}"
    return type_def.name


#: List of linear extension types that correspond to affine Guppy types and thus require
#: insertion of an explicit drop operation.
AFFINE_EXTENSION_TYS: list[str] = [
    qualified_name(ARRAY_EXTENSION.get_type("array")),
    qualified_name(BORROW_ARRAY_EXTENSION.get_type("borrow_array")),
]


def requires_drop(ty: ht.Type) -> bool:
    """Checks if a Hugr type requires an implicit drop op insertion.
    This is the case for linear Hugr types that correspond to affine Guppy types, or
    any other type containing one of those. See `AFFINE_EXTENSION_TYS`.
    """
    match ty:
        case ht.ExtType(type_def=type_def, args=args):
            return qualified_name(type_def) in AFFINE_EXTENSION_TYS or any(
                requires_drop(arg.ty) for arg in args if isinstance(arg, ht.TypeTypeArg)
            )
        case ht.Opaque(id=name, extension=extension, args=args):
            qualified = f"{extension}.{name}" if extension else name
            return qualified in AFFINE_EXTENSION_TYS or any(
                requires_drop(arg.ty) for arg in args if isinstance(arg, ht.TypeTypeArg)
            )
        case ht.Sum(variant_rows=rows):
            return any(requires_drop(ty) for row in rows for ty in row)
        case ht.Variable(bound=bound):
            return bound == ht.TypeBound.Linear
        case ht.FunctionType():
            return False
        case ht.Alias():
            raise InternalGuppyError("Alias should not be emitted!")
        case _:
            return False


def drop_op(ty: ht.Type) -> ops.ExtOp:
    """Returns the operation to drop affine values."""
    return GUPPY_EXTENSION.get_op("drop").instantiate(
        [ht.TypeTypeArg(ty)], ht.FunctionType([ty], [])
    )


def insert_drops(hugr: Hugr[OpVarCov]) -> None:
    """Inserts explicit drop ops for unconnected ports into the Hugr.
    TODO: This is a quick workaround until we can properly insert these drops during
      linearity checking. See https://github.com/quantinuum/guppylang/issues/1082
    """
    for node in hugr:
        data = hugr[node]
        # Iterating over `node.outputs()` doesn't work reliably since it sometimes
        # raises an `IncompleteOp` exception. Instead, we query the number of out ports
        # and look them up by index. However, this method is *also* broken when
        # inspecting `FuncDefn` nodes due to https://github.com/quantinuum/hugr/issues/2438.
        if isinstance(data.op, ops.FuncDefn):
            continue
        for i in range(hugr.num_out_ports(node)):
            port = node.out(i)
            kind = hugr.port_kind(port)
            if (
                next(iter(hugr.linked_ports(port)), None) is None
                and isinstance(kind, ht.ValueKind)
                and requires_drop(kind.ty)
            ):
                drop = hugr.add_node(drop_op(kind.ty), parent=data.parent)
                hugr.add_link(port, drop.inp(0))
