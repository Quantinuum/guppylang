import itertools
from abc import ABC
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from hugr import Hugr, Wire
from hugr import tys as ht
from hugr.build import function as hf
from hugr.build.dfg import DefinitionBuilder
from hugr.hugr.base import OpVarCov
from hugr.ops import Module
from hugr.std.collections.array import EXTENSION as ARRAY_EXTENSION
from hugr.std.collections.borrow_array import EXTENSION as BORROW_ARRAY_EXTENSION

from guppylang_internals.checker.core import (
    FieldAccess,
    Place,
    PlaceId,
    TupleAccess,
    Variable,
)
from guppylang_internals.checker.modifier import CustomModifierKind
from guppylang_internals.compiler.builder import ops
from guppylang_internals.definition.common import (
    CompilableDef,
    CompiledDef,
    DefId,
    Definition,
    RawDef,
)
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.definition.value import CompiledCallableDef
from guppylang_internals.engine import (
    DEF_STORE,
    ENGINE,
    CompilationStage,
    ConcreteCustomUse,
    MonoDefId,
)
from guppylang_internals.error import InternalGuppyError
from guppylang_internals.metadata.common import (
    FunctionMetadata,
    add_metadata,
    add_num_control_qubits,
)
from guppylang_internals.metadata.debug_info_util import StringTable
from guppylang_internals.std._internal.compiler.tket_exts import (
    DEBUG_EXTENSION as TKET_DEBUG_EXTENSION,
)
from guppylang_internals.std._internal.compiler.tket_exts import (
    GUPPY_EXTENSION,
)
from guppylang_internals.std._internal.compiler.tket_exts import (
    QUANTUM_EXTENSION as TKET_QUANTUM_EXTENSION,
)
from guppylang_internals.std._internal.compiler.tket_exts import (
    RESULT_EXTENSION as TKET_RESULT_EXTENSION,
)
from guppylang_internals.tys.common import ToHugrContext
from guppylang_internals.tys.subst import Inst
from guppylang_internals.tys.ty import (
    StructType,
    TupleType,
    Type,
)

if TYPE_CHECKING:
    from guppylang_internals.compiler.builder import DFBuilder
    from guppylang_internals.definition.function import CompiledFunctionDef
    from guppylang_internals.tys import Effect

CompiledLocals = dict[PlaceId, Wire]


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


#: Unique identifier for global Hugr constants and monomorphized functions
MonoGlobalConstId = tuple[GlobalConstId, Inst]


class CompilerContext(ToHugrContext):
    """Compilation context containing all available definitions.

    Maintains a `worklist` of definitions which have been used by other compiled code
    (i.e. `compile_outer` has been called) but have not yet been compiled/lowered
    themselves (i.e. `compile_inner` has not yet been called).
    """

    module: DefinitionBuilder[Module]

    #: The definitions compiled so far. For generic definitions, their id can occur
    #: multiple times here with respectively different monomorphizations. See
    #: `MonoDefId` and `MonoArgs` for details.
    compiled: dict[MonoDefId, CompiledDef]

    # use dict over set for deterministic iteration order
    worklist: dict[MonoDefId, None]

    global_funcs: dict[MonoGlobalConstId, hf.Function]

    #: The definitions that should be exported (i.e. made public) in the Hugr module
    #: currently being built. For compilation of single entrypoints, this will be just
    #: that entrypoint, while for compilation of libraries this will contain all
    #: functions that are part of its public interface.
    exported_defs: set[DefId]

    metadata_file_table: StringTable

    # Info computed from callgraph before compilation begins
    effects: Mapping[MonoDefId, frozenset["Effect"]]

    #: Concrete custom modifier implementations grouped by parent monomorphization.
    custom_uses_by_parent: dict[MonoDefId, list[ConcreteCustomUse]]

    def __init__(
        self,
        module: DefinitionBuilder[Module],
        exported_defs: set[DefId],
        effects: Mapping[MonoDefId, frozenset["Effect"]],
        concrete_custom_uses: Mapping[MonoDefId, ConcreteCustomUse],
        file_table: StringTable | None = None,
    ) -> None:
        self.module = module
        self.worklist = {}
        self.compiled = {}
        self.global_funcs = {}
        self.exported_defs: set[DefId] = exported_defs
        self.effects = effects
        self.custom_uses_by_parent = {}
        # Group concrete custom uses by parent monomorphization.
        for implementation, custom_use in concrete_custom_uses.items():
            assert implementation == custom_use.implementation
            self.custom_uses_by_parent.setdefault(custom_use.parent, []).append(
                custom_use
            )
        self.metadata_file_table = (
            file_table if file_table is not None else StringTable([])
        )

    def build_compiled_def(self, def_id: DefId, type_args: Inst | None) -> CompiledDef:
        """Returns the compiled definitions corresponding to the given ID.

        Might mutate the current Hugr if this definition has never been compiled before.
        """
        mono_args = type_args or ()
        if (def_id, mono_args) not in self.compiled:
            defn = ENGINE.get_checked(def_id, mono_args)
            # During compilation stage, get_checked will not have done any checking.
            # (During checking stage, this will fail, but we might have done more
            # checking. We could avoid this side effect, but it'd be more work.)
            ENGINE.assert_stage(CompilationStage.COMPILE, f"build_compiled_def {defn}")
            if isinstance(defn, CompilableDef):
                defn = defn.compile_outer(self.module, self)
            self.compiled[def_id, mono_args] = defn
            self.worklist[def_id, mono_args] = None

            if (def_id, mono_args) in self.custom_uses_by_parent:
                daggered, controlled, ctrl_daggered = (
                    self._compile_custom_modifier_uses((def_id, mono_args))
                )
                from guppylang_internals.definition.function import (
                    CompiledFunctionDef,
                )

                assert isinstance(defn, CompiledFunctionDef)
                metadata = FunctionMetadata()
                metadata.set_modified_defs(
                    daggered=daggered,
                    controlled=controlled,
                    ctrl_daggered=ctrl_daggered,
                )
                add_metadata(
                    self.module.hugr[defn.hugr_node].metadata,
                    metadata,
                )

        return self.compiled[def_id, mono_args]

    # NICOLA: there are a lot for loop packing and unpacking custom modifier uses, can we avoid this  # noqa: E501
    def _compile_custom_modifier_uses(
        self, parent: MonoDefId
    ) -> tuple[str | None, list[str] | None, list[str] | None]:
        """Compiles a parent's concrete custom uses and builds its metadata values."""
        custom_uses = self.custom_uses_by_parent[parent]

        # Group custom implementations by modification kind.
        by_kind: dict[CustomModifierKind, list[ConcreteCustomUse]] = {}
        for custom_use in custom_uses:
            assert custom_use.parent == parent
            by_kind.setdefault(custom_use.kind, []).append(custom_use)

        daggered: str | None = None
        controlled: list[str] | None = None
        ctrl_daggered: list[str] | None = None
        for kind, kind_uses in by_kind.items():
            if kind == CustomModifierKind.DAGGERED:
                # Daggered implementations is not generic, thus must have exactly one
                # concrete implementation (i.e. the original one).
                assert len(kind_uses) == 1
                daggered = self._compile_custom_modifier_use(kind_uses[0]).link_name
                continue

            assert kind.takes_controls
            # Group uses by number of control qubits required
            uses_by_control_count: list[tuple[int, ConcreteCustomUse]] = []
            for custom_use in kind_uses:
                assert custom_use.control_count is not None
                uses_by_control_count.append((custom_use.control_count, custom_use))

            custom_implementation_names: list[str] = []
            for control_count, custom_use in sorted(
                uses_by_control_count, key=lambda item: item[0]
            ):
                compiled_custom = self._compile_custom_modifier_use(custom_use)
                add_num_control_qubits(
                    self.module.hugr[compiled_custom.hugr_node].metadata,
                    control_count,
                )
                custom_implementation_names.append(compiled_custom.link_name)

            if kind == CustomModifierKind.CONTROLLED:
                controlled = custom_implementation_names
            else:
                assert kind == CustomModifierKind.CTRL_DAGGERED
                ctrl_daggered = custom_implementation_names

        return daggered, controlled, ctrl_daggered

    def _compile_custom_modifier_use(
        self, custom_use: ConcreteCustomUse
    ) -> "CompiledFunctionDef":
        """Compiles one custom implementation already prepared during checking."""
        from guppylang_internals.definition.function import CompiledFunctionDef

        assert custom_use.implementation in ENGINE.checked
        custom_id, custom_args = custom_use.implementation
        compiled = self.build_compiled_def(custom_id, custom_args)
        assert isinstance(compiled, CompiledFunctionDef)
        return compiled

    def iterate_worklist(self) -> None:
        while self.worklist:
            next_id, next_mono_args = self.worklist.popitem()[0]
            next_def = self.compiled[next_id, next_mono_args]
            next_def.compile_inner(self)

        # Insert explicit drops for affine types
        # TODO: This is a quick workaround until we can properly insert these drops
        # during linearity checking. See https://github.com/quantinuum/guppylang/issues/1082
        insert_drops(self.module.hugr)

    def build_compiled_instance_func(
        self,
        ty: Type | TypeDef,
        name: str,
        type_args: Inst,
    ) -> CompiledCallableDef | None:
        """Returns s compiled instance method along, or `None` if the type doesn't have
        a matching method.

        Compiles the definition and all of its dependencies into the current Hugr.
        """
        from guppylang_internals.engine import ENGINE

        parsed_func = ENGINE.get_instance_func(ty, name)
        if parsed_func is None:
            return None
        checked_func = ENGINE.get_checked(parsed_func.id, type_args)
        compiled_func = self.build_compiled_def(checked_func.id, type_args)
        assert isinstance(compiled_func, CompiledCallableDef)
        return compiled_func

    def declare_global_func(
        self,
        const_id: GlobalConstId,
        func_ty: ht.PolyFuncType,
        type_args: Inst | None = None,
    ) -> tuple[hf.Function, bool]:
        """
        Creates a function builder for a global function if it doesn't already exist,
        else returns the existing one.
        """
        mono_args = type_args or ()
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


@dataclass
class DFContainer:
    """A dataflow graph under construction.

    This class is passed through the entire compilation pipeline and stores a builder
    for the dataflow child-graph currently being constructed as well as all live local
    variables. Note that the variable map is mutated in-place and always reflects the
    current compilation state.
    """

    builder: "DFBuilder"
    ctx: CompilerContext
    locals: CompiledLocals = field(default_factory=dict)

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
        wire = self.builder.add_op(ops.make_tuple(child_types), *child_wires)[0]
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
            hugr_fields_ty = [t.ty.to_hugr(self.ctx) for t in place.ty.fields]
            unpack = self.builder.add_op(ops.unpack_tuple(hugr_fields_ty), port)
            for field, field_port in zip(place.ty.fields, unpack, strict=True):
                self[FieldAccess(place, field, None)] = field_port
            # If we had a previous wire assigned to this place, we need forget about it.
            # Otherwise, we might use this old value when looking up the place later
            self.locals.pop(place.id, None)
        # Same for tuples.
        elif isinstance(place.ty, TupleType) and not is_return:
            hugr_elem_tys = [ty.to_hugr(self.ctx) for ty in place.ty.element_types]
            unpack = self.builder.add_op(ops.unpack_tuple(hugr_elem_tys), port)
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
    if parent_ty_id := DEF_STORE.type_member_parents.get(defn.id):
        return DEF_STORE.raw_defs[parent_ty_id]
    else:
        return None


QUANTUM_EXTENSION = TKET_QUANTUM_EXTENSION
RESULT_EXTENSION = TKET_RESULT_EXTENSION
DEBUG_EXTENSION = TKET_DEBUG_EXTENSION


#: List of linear extension types that correspond to affine Guppy types and thus require
#: insertion of an explicit drop operation.
AFFINE_EXTENSION_TYS: list[str] = [
    ARRAY_EXTENSION.get_type("array").qualified_name(),
    BORROW_ARRAY_EXTENSION.get_type("borrow_array").qualified_name(),
]


def requires_drop(ty: ht.Type) -> bool:
    """Checks if a Hugr type requires an implicit drop op insertion.
    This is the case for linear Hugr types that correspond to affine Guppy types, or
    any other type containing one of those. See `AFFINE_EXTENSION_TYS`.
    """
    match ty:
        case ht.ExtType(type_def=type_def, args=args):
            return type_def.qualified_name() in AFFINE_EXTENSION_TYS or any(
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


def insert_drops(hugr: Hugr[OpVarCov]) -> None:
    """Inserts explicit drop ops for unconnected ports into the Hugr.
    TODO: This is a quick workaround until we can properly insert these drops during
      linearity checking. See https://github.com/quantinuum/guppylang/issues/1082
    """
    for node in hugr:
        data = hugr[node]
        # Iterating over `node.outputs()` doesn't work reliably since it sometimes
        # raises an `IncompleteOp` exception. Instead, we query the number of out ports
        # and look them up by index.
        for i in range(hugr.num_out_ports(node)):
            port = node.out(i)
            kind = hugr.port_kind(port)
            if (
                next(iter(hugr.linked_ports(port)), None) is None
                and isinstance(kind, ht.ValueKind)
                and requires_drop(kind.ty)
            ):
                drop_op = GUPPY_EXTENSION.get_op("drop").instantiate(
                    [ht.TypeTypeArg(kind.ty)], ht.FunctionType([kind.ty], [])
                )
                drop = hugr.add_node(drop_op, parent=data.parent)
                hugr.add_link(port, drop.inp(0))
