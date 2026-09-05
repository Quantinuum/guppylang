import ast
from collections import defaultdict
from collections.abc import Generator, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import FrameType
from typing import TYPE_CHECKING, ClassVar, assert_never, cast

import hugr
import hugr.build.function as hf
from hugr.debug_info import DICompileUnit
from hugr.envelope import ExtensionDesc, GeneratorDesc
from hugr.ext import Extension, ExtensionRegistry
from hugr.metadata import HugrDebugInfo, HugrGenerator, HugrUsedExtensions
from hugr.ops import FuncDecl
from hugr.package import ModulePointer, Package
from semver import Version

import guppylang_internals
from guppylang_internals.analysis.callgraph import CallGraph
from guppylang_internals.analysis.effects import compute_effects
from guppylang_internals.analysis.modifier_callgraph import (
    ConcreteCustomUse,
    EdgeWithModifierContext,
    analyze_modifier_calls,
)
from guppylang_internals.checker.modifier import (
    CustomModifierKind,
    ModifierContext,
)
from guppylang_internals.debug_mode import debug_mode_enabled
from guppylang_internals.definition.common import (
    CheckableDef,
    CheckableGenericDef,
    CheckedDef,
    CompiledDef,
    DefId,
    ParsableDef,
    ParsedDef,
    RawDef,
)
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.definition.value import (
    CallableDef,
    CallableEffects,
    CompiledCallableDef,
    CompiledHugrNodeDef,
)
from guppylang_internals.diagnostic import Error, Note
from guppylang_internals.error import (
    GuppyError,
    InternalGuppyError,
    RequiresMonomorphizationError,
    pretty_errors,
)
from guppylang_internals.frame_util import get_calling_frame
from guppylang_internals.metadata.debug_info_util import (
    StringTable,
)
from guppylang_internals.span import SourceMap
from guppylang_internals.tys.arg import ConstArg, TypeArg
from guppylang_internals.tys.builtin import (
    array_type,
    array_type_def,
    bool_type_def,
    callable_protocol_def,
    controllable_protocol_def,
    daggerable_protocol_def,
    float_type_def,
    frozenarray_type_def,
    function_def_type_def,
    function_type_def,
    get_array_length,
    get_element_type,
    int_type_def,
    is_array_type,
    list_type_def,
    nat_type,
    nat_type_def,
    none_type_def,
    option_type_def,
    self_type_def,
    sized_iter_type_def,
    string_type_def,
    tuple_type_def,
    unitary_protocol_def,
)
from guppylang_internals.tys.const import BoundConstVar, ConstValue
from guppylang_internals.tys.param import ConstParam, Parameter
from guppylang_internals.tys.printing import TypePrinter
from guppylang_internals.tys.qubit import is_qubit_ty, qubit_ty
from guppylang_internals.tys.subst import Inst, is_concrete_inst
from guppylang_internals.tys.ty import (
    CALL_CONTROLLED_METHOD,
    CALL_CTRL_DAGGERED_METHOD,
    CALL_DAGGERED_METHOD,
    BoundTypeVar,
    EnumType,
    ExistentialTypeVar,
    FuncInput,
    FunctionDefType,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
    OpaqueType,
    StructType,
    TupleType,
    Type,
    unify,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from guppylang_internals.ast_util import AstNode
    from guppylang_internals.checker.core import Context, Globals
    from guppylang_internals.definition.function import ParsedFunctionDef
    from guppylang_internals.tys import Effect


BUILTIN_DEFS_LIST: list[RawDef] = [
    function_type_def,
    function_def_type_def,
    unitary_protocol_def,
    daggerable_protocol_def,
    controllable_protocol_def,
    self_type_def,
    tuple_type_def,
    none_type_def,
    bool_type_def,
    nat_type_def,
    int_type_def,
    float_type_def,
    string_type_def,
    list_type_def,
    array_type_def,
    frozenarray_type_def,
    sized_iter_type_def,
    option_type_def,
    callable_protocol_def,
]

BUILTIN_DEFS = {defn.name: defn for defn in BUILTIN_DEFS_LIST}

#: Identifier for a monomorphized version of a definition.
#:
#: Kinds of definitions that are never generic (e.g. constant definitions) and
#: definitions without generic parameters (e.g. a non-generic function definition) are
#: registered with an empty tuple () as `Inst`. Otherwise, `Inst` will be the
#: instantiation for the generic parameters for the monomorphized version.
MonoDefId = tuple[DefId, Inst]

#: An edge in the monomorphized call graph, represented as `(caller, callee)`.
CallGraphEdge = tuple[MonoDefId, MonoDefId]


class CompilationStage(Enum):
    NONE = "none"
    CHECK = "check"
    COMPILE = "compile"


class DefinitionStore:
    """Storage class holding references to all Guppy definitions created in the current
    interpreter session.

    See `DEF_STORE` for the singleton instance of this class.
    """

    raw_defs: dict[DefId, RawDef]
    type_members: defaultdict[DefId, dict[str, DefId]]
    type_member_parents: dict[DefId, DefId]
    wasm_functions: dict[DefId, FunctionType]
    frames: dict[DefId, FrameType]
    sources: SourceMap
    # Maps a parent definition (usually a function) to its custom modified definitions
    custom_modified_defs: dict[DefId, dict[CustomModifierKind, DefId]]

    def __init__(self) -> None:
        self.raw_defs = {defn.id: defn for defn in BUILTIN_DEFS_LIST}
        self.type_members = defaultdict(dict)
        self.type_member_parents = {}
        self.frames = {}
        self.sources = SourceMap()
        self.wasm_functions = {}
        self.custom_modified_defs = defaultdict(dict)

    def register_def(self, defn: RawDef, frame: FrameType) -> None:
        self.raw_defs[defn.id] = defn
        self.frames[defn.id] = frame

    def register_type_member(self, ty_id: DefId, name: str, member_id: DefId) -> None:
        assert member_id not in self.type_member_parents, "Already a type member"
        self.type_members[ty_id][name] = member_id
        self.type_member_parents[member_id] = ty_id
        # Update the frame of the definition to the frame of the defining class
        if member_id in self.frames:
            frame = self.frames[member_id].f_back
            if frame:
                self.frames[member_id] = frame
                # For Python 3.12 generic functions and classes, there is an additional
                # inserted frame for the annotation scope. We can detect this frame by
                # looking for the special ".generic_base" variable in the frame locals
                # that is implicitly inserted by CPython. See
                # - https://docs.python.org/3/reference/executionmodel.html#annotation-scopes
                # - https://docs.python.org/3/reference/compound_stmts.html#generic-functions
                # - https://jellezijlstra.github.io/pep695.html
                if ".generic_base" in frame.f_locals:
                    frame = frame.f_back
                    assert frame is not None
                    self.frames[member_id] = frame

    def register_wasm_function(self, fn_id: DefId, sig: FunctionType) -> None:
        self.wasm_functions[fn_id] = sig

    def register_custom_modified_def(
        self,
        parent_def_id: DefId,
        kind: CustomModifierKind,
        custom_def_id: DefId,
    ) -> None:
        custom_defs = self.custom_modified_defs[parent_def_id]
        assert kind not in custom_defs, f"Custom {kind.value} already registered"
        custom_defs[kind] = custom_def_id


DEF_STORE: DefinitionStore = DefinitionStore()


@dataclass(frozen=True)
class MonoArgsNote(Note):
    message: ClassVar[str] = "Error occurred while checking the instantiation {inst}"
    params: Sequence[Parameter]
    mono_args: Inst

    @property
    def inst(self) -> str:
        printer = TypePrinter()
        return ",".join(
            f"`{param.name} := {printer.visit(arg)}`"
            for param, arg in zip(self.params, self.mono_args, strict=True)
        )


class CompilationEngine:
    """Main compiler driver handling checking and compiling of definitions.

    The engine maintains a worklist of definitions that still need to be checked and
    makes sure that all dependencies are compiled.

    See `ENGINE` for the singleton instance of this class.
    """

    parsed: dict[DefId, ParsedDef]
    checked: dict[MonoDefId, CheckedDef]
    compiled: dict[MonoDefId, CompiledDef]
    additional_extensions: list[Extension]

    types_to_check_worklist: dict[DefId, ParsedDef]
    #: Generic functions
    generic_to_check_worklist: dict[DefId, CheckableGenericDef]
    to_check_worklist: dict[MonoDefId, ParsedDef]

    to_compile_worklist: dict[MonoDefId, CheckedDef]

    #: Call graph mapping from caller to list of callees. Populated during type checking
    # as calls are checked, to be then used for effects checking.
    call_graph: dict[MonoDefId, list[MonoDefId]]
    func_effects: dict[MonoDefId, set["Effect"]]
    #: Distinct modifier contexts used on each monomorphized call-graph edge. The value
    #: stores one representative call site for future diagnostics.
    local_modifiers_by_edge: dict[CallGraphEdge, dict[ModifierContext, "AstNode"]]
    #: Resolved calls indexed by their raw edge and effective propagated context.
    resolved_modified_calls: dict[EdgeWithModifierContext, MonoDefId]
    #: Concrete custom modifier uses indexed by custom-definition monomorphization.
    custom_uses_by_mono_def: dict[MonoDefId, ConcreteCustomUse]

    # Cached compilation infrastructure (lazy-initialized, program-independent)
    _base_resolve_registry: ExtensionRegistry | None = None

    _stage: CompilationStage = CompilationStage.NONE

    def __init__(self) -> None:
        """Resets the compilation cache."""
        self.reset()
        self.additional_extensions = []

    @contextmanager
    def _in_stage(self, stage: CompilationStage) -> Generator[None, None, None]:
        old_stage = self._stage
        self._stage = stage
        try:
            yield
        finally:
            self._stage = old_stage

    @staticmethod
    def _get_base_resolve_registry() -> ExtensionRegistry:
        """Get the base resolve registry with standard extensions.

        Cached at class level.
        """
        if CompilationEngine._base_resolve_registry is None:
            from guppylang_internals.compiler import hugr_extension
            from guppylang_internals.std._internal.compiler.tket_exts import (
                TKET_EXTENSIONS,
            )

            registry = ExtensionRegistry()
            for ext in [
                *hugr.std._std_extensions().extensions,
                *TKET_EXTENSIONS,
                hugr_extension.EXTENSION,
            ]:
                registry.register(ext)
            CompilationEngine._base_resolve_registry = registry
        return CompilationEngine._base_resolve_registry

    def reset(self) -> None:
        """Resets the compilation cache."""
        self.parsed = {}
        self.checked = {}
        self.compiled = {}
        self.to_check_worklist = {}
        self.generic_to_check_worklist = {}
        self.types_to_check_worklist = {}
        self.call_graph = {}
        self.func_effects = {}
        self.local_modifiers_by_edge = {}
        self.resolved_modified_calls = {}
        self.custom_uses_by_mono_def = {}

    def register_call(
        self,
        ctx: "Context",
        callee: "CallableDef",
        inst: Inst,
        call_node: "AstNode",
    ) -> None:
        """Registers a function call in the call graph. If the callee is a
        `CallableEffects` then also registers those effects for that callee."""
        # current_caller is not set for e.g. comptime but should be here:
        assert ctx.current_caller is not None
        assert ctx.current_caller in self.call_graph
        self.call_graph[ctx.current_caller].append((callee.id, inst))
        if isinstance(callee, CallableEffects):
            self.register_effects((callee.id, inst), callee.call_effects)
        elif isinstance(callee, CallableDef):
            # Effects not known yet, will be computed.
            callee_mono_def_id: MonoDefId = (callee.id, inst)
            edge = (ctx.current_caller, callee_mono_def_id)
            modifier_contexts = self.local_modifiers_by_edge.setdefault(edge, {})
            modifier_contexts.setdefault(ctx.modifier_ctx, call_node)

    def register_effects(self, func: MonoDefId, effects: "Iterable[Effect]") -> None:
        """Registers known effects for a function, for when the effects cannot be
        attributed to some concrete callee (i.e. with its own MonoDefId)."""
        self.func_effects.setdefault(func, set()).update(effects)

    def assert_stage(self, stage: CompilationStage, context: str) -> None:
        if self._stage != stage:
            raise CompilationStageError(
                context, actual_stage=self._stage, expected_stage=stage
            )

    @pretty_errors
    def get_parsed(self, id: DefId) -> ParsedDef:
        """Look up the parsed version of a definition by its id.

        If in checking stage, parses the definition if it hasn't been already.
        Also makes sure that the definition will be checked and compiled later on.
        """
        from guppylang_internals.checker.core import Globals

        if id in self.parsed:
            return self.parsed[id]

        if self._stage == CompilationStage.NONE:
            with self._in_stage(CompilationStage.CHECK):
                return self.get_parsed(id)

        defn = DEF_STORE.raw_defs[id]
        if isinstance(defn, ParsableDef):
            self.assert_stage(CompilationStage.CHECK, f"parse {defn}")
            defn = defn.parse(Globals(DEF_STORE.frames[defn.id]), DEF_STORE.sources)

        self.parsed[id] = defn
        if isinstance(defn, TypeDef):
            self.assert_stage(CompilationStage.CHECK, f"parse {defn}")
            self.types_to_check_worklist[id] = defn
        elif isinstance(defn, CheckableDef):
            self.assert_stage(CompilationStage.CHECK, f"parse {defn}")
            self.to_check_worklist[id, ()] = defn
        elif isinstance(defn, CheckableGenericDef) and defn.params:
            # If `defn` is a `CheckableGenericDef`, we can't add it to the worklist yet
            # since we don't know the generic instantiation yet. It will be added when
            # we're checking a use of the definition (e.g. a call). See for example
            # `ParsedFunctionDef.check_call`.
            self.assert_stage(CompilationStage.CHECK, f"parse {defn}")
            self.generic_to_check_worklist[id] = defn

        # If `defn` has any custom modified definitions linked to it,
        # we need to make sure that they are also parsed.
        custom_modified_defs = DEF_STORE.custom_modified_defs.get(defn.id, {})
        if custom_modified_defs:
            # Only CallableDef can have custom modified definitions
            assert isinstance(defn, CallableDef)
            for custom_def_id in custom_modified_defs.values():
                parsed_custom_defn = self.get_parsed(custom_def_id)
                from guppylang_internals.definition.function import ParsedFunctionDef

                assert isinstance(parsed_custom_defn, ParsedFunctionDef)
                _check_modified_def_signature(parsed_custom_defn, defn.ty)
                # While parameterized custom methods (controlled and ctrl_daggered) are
                # scheduled for check by `get_parsed`, (see
                # ```
                # 412| elif isinstance(defn, CheckableGenericDef) and defn.params:
                # ```
                # ), non-parameterized custom methods (daggered) are not scheduled
                # thus we explicitly schedule them here. This ensure that all custom
                # methods are checked even if not used.
                if not parsed_custom_defn.params:
                    self.to_check_worklist[custom_def_id, ()] = parsed_custom_defn
        return defn

    @pretty_errors
    def get_checked(self, id: DefId, mono_args: Inst) -> CheckedDef:
        """Look up the checked version of a definition by its id.

        If in checking stage, parses & checks the definition if it hasn't been already.
        Also makes sure that the definition will be compiled to Hugr later on.
        """
        from guppylang_internals.checker.core import Globals

        if (id, mono_args) in self.checked:
            return self.checked[id, mono_args]

        if self._stage == CompilationStage.NONE:
            with self._in_stage(CompilationStage.CHECK):
                return self.get_checked(id, mono_args)

        defn = self.get_parsed(id)
        if isinstance(defn, CheckableDef):
            self.assert_stage(CompilationStage.CHECK, f"check {defn}")
            defn = defn.check(Globals(DEF_STORE.frames[defn.id]))
        elif isinstance(defn, CheckableGenericDef):
            self.assert_stage(CompilationStage.CHECK, f"check {defn}")
            defn = _check_generic_def_instantiation(
                defn, mono_args, Globals(DEF_STORE.frames[defn.id])
            )
        self.checked[id, mono_args] = defn

        from guppylang_internals.definition.enum import CheckedEnumDef
        from guppylang_internals.definition.struct import CheckedStructDef

        if isinstance(defn, CheckedStructDef | CheckedEnumDef):
            for method_def in defn.generated_methods():
                DEF_STORE.register_def(method_def, DEF_STORE.frames[id])
                DEF_STORE.register_type_member(defn.id, method_def.name, method_def.id)

        return defn

    def register_generic_use(self, defn: CheckableGenericDef, type_args: Inst) -> None:
        """Tells the engine that an instantiation of a generic definition has been
        used.

        Adds the instantiation to the worklist and ensures that it will be checked.
        """
        if is_concrete_inst(type_args):
            self.to_check_worklist[defn.id, type_args] = defn

    def register_call_graph_node(self, mono_id: MonoDefId) -> None:
        """Ensures a monomorphized definition is registered in the call graph.
        Required before edges can be added from the node, but not to it.

        Thus, used to indicate the def is of a kind for which we wish to track calls
        (i.e. a user-defined function), even if it doesn't actually contain any.
        """
        assert mono_id not in self.call_graph
        self.call_graph[mono_id] = []

    def get_type_defn(self, ty: Type | TypeDef) -> TypeDef | None:
        """Convert a Type | TypeDef to a TypeDef."""
        type_defn: TypeDef
        match ty:
            case TypeDef() as type_defn:
                pass
            case BoundTypeVar() | ExistentialTypeVar():
                return None
            case NumericType(kind):
                match kind:
                    case NumericType.Kind.Nat:
                        type_defn = nat_type_def
                    case NumericType.Kind.Int:
                        type_defn = int_type_def
                    case NumericType.Kind.Float:
                        type_defn = float_type_def
                    case kind:
                        return assert_never(kind)
            case FunctionType():
                type_defn = function_type_def
            case FunctionDefType():
                type_defn = function_def_type_def
            case OpaqueType() as ty:
                type_defn = ty.defn
            case StructType() as ty:
                type_defn = ty.defn
            case TupleType():
                type_defn = tuple_type_def
            case NoneType():
                type_defn = none_type_def
            case EnumType():
                type_defn = ty.defn
            case _:
                return assert_never(ty)

        type_defn = cast("TypeDef", ENGINE.get_checked(type_defn.id, mono_args=()))
        return type_defn

    def get_instance_func(self, ty: Type | TypeDef, name: str) -> CallableDef | None:
        """Looks up an instance function with a given name for a type.

        Returns `None` if the name doesn't exist or isn't a function.
        """
        type_defn = self.get_type_defn(ty)
        if type_defn is None:
            return None
        if (
            type_defn.id in DEF_STORE.type_members
            and name in DEF_STORE.type_members[type_defn.id]
        ):
            def_id = DEF_STORE.type_members[type_defn.id][name]
            defn = ENGINE.get_parsed(def_id)
            if isinstance(defn, CallableDef):
                return defn
        return None

    def get_type_member(self, ty: Type | TypeDef, name: str) -> DefId | None:
        """Looks up a type member with a given name for a type.

        Returns `None` if the name doesn't exist
        """
        type_defn = self.get_type_defn(ty)
        if type_defn is None:
            return None
        if (
            type_defn.id in DEF_STORE.type_members
            and name in DEF_STORE.type_members[type_defn.id]
        ):
            return DEF_STORE.type_members[type_defn.id][name]
        return None

    def is_def_static(self, func_id: DefId) -> bool:
        """Get staticness of parsed definition if it can be static."""

        parsed = self.get_parsed(func_id)
        return isinstance(parsed, CallableDef) and parsed.is_static

    @pretty_errors
    def check_single(self, id: DefId) -> None:
        """Top-level function to kick of checking of a definition.

        This is the main driver behind `guppy.check()`.
        """
        self.check([id])

    @pretty_errors
    def check(self, def_ids: list[DefId], *, reset: bool = True) -> None:
        """Top-level function to kick of checking of multiple definitions.

        This is the main driver behind `guppy.library(...).check()`.
        """
        # Clear previous compilation cache.
        # TODO: In order to maintain results from the previous `check` call we would
        #  need to store and check if any dependencies have changed.
        if reset:
            self.reset()

        # We allow generic functions as checking entrypoints as long as we don't run
        # into a check that requires monomorphization. For this, we check a version
        # where all parameters are instantiated to opaque `BoundVariable`s.
        entry_points: list[MonoDefId] = []
        for def_id in def_ids:
            entry_defn = self.get_parsed(def_id)
            entry_params = (
                entry_defn.params if isinstance(entry_defn, CheckableGenericDef) else []
            )
            entry_mono_args = tuple(param.to_bound() for param in entry_params)
            entry_points.append((def_id, entry_mono_args))
            try:
                self.checked[def_id, entry_mono_args] = self.get_checked(
                    def_id, entry_mono_args
                )
            except RequiresMonomorphizationError as e:
                # `RequiresMonomorphizationError` is raised whenever we cannot proceed
                # checking without having the monomorphization available. In that case,
                # we give up and prompt the user to specify the generic arguments.
                assert isinstance(entry_defn, CheckableGenericDef)
                err = EntryCheckMonomorphizeError(entry_defn.defined_at, entry_defn)
                raise GuppyError(err) from e

        # Checking the entrypoint will have populated the worklist, so now we need to
        # process it.
        # Propagate the locally checked modifier labels through the call graph. A
        # resolved custom implementation can introduce more checked graph nodes, so
        # repeat the complete contextual analysis until monomorphization reaches a
        # fixed point.
        self._drain_check_worklists()
        while True:
            modifier_analysis = analyze_modifier_calls(
                entry_points,
                self.call_graph,
                self.local_modifiers_by_edge,
                self._resolve_modified_call,
            )
            self.resolved_modified_calls = modifier_analysis.resolved_calls
            self.custom_uses_by_mono_def = modifier_analysis.custom_uses_by_mono_def
            if not self._register_custom_modifier_monomorphizations(
                self.custom_uses_by_mono_def.values()
            ):
                self.call_graph = modifier_analysis.expanded_calls
                break
            self._drain_check_worklists()

    def _drain_check_worklists(self) -> None:
        """Checks all definitions currently queued on the checking worklists."""
        while (
            self.types_to_check_worklist
            or self.generic_to_check_worklist
            or self.to_check_worklist
        ):
            # Types need to be checked first. This is because parsing e.g. a function
            # definition requires instantiating the types in its signature which can
            # only be done if the types have already been checked.
            if self.types_to_check_worklist:
                id, _ = self.types_to_check_worklist.popitem()
                mono_args: Inst = ()
                self.checked[id, mono_args] = self.get_checked(id, mono_args)
            # For generic functions, we first check a version where all parameters are
            # instantiated to opaque `BoundVariable`s. This way, we'll get nicer error
            # messages e.g. for type mismatches with generic parameters. The concrete
            # monomorphic instantiations will be checked later via the regular worklist.
            elif self.generic_to_check_worklist:
                id, defn = self.generic_to_check_worklist.popitem()
                mono_args = tuple(param.to_bound() for param in defn.params)
                # `RequiresMonomorphizationError` is raised whenever we cannot proceed
                # checking without having the monomorphization available. In that case,
                # we just gve up and wait for the proper monomorphic check later.
                with suppress(RequiresMonomorphizationError):
                    self.checked[id, mono_args] = self.get_checked(id, mono_args)
            else:
                (id, mono_args), _ = self.to_check_worklist.popitem()
                self.checked[id, mono_args] = self.get_checked(id, mono_args)

    def _register_custom_modifier_monomorphizations(
        self, custom_uses: "Iterable[ConcreteCustomUse]"
    ) -> bool:
        """Adds required custom-definition monomorphizations to the checking worklist.

        Returns whether at least one corresponding monomorphization was added to the
        checking worklist.
        """
        added = False
        for custom_use in custom_uses:
            custom_def = custom_use.custom_def
            if custom_def in self.checked or custom_def in self.to_check_worklist:
                continue
            custom_id, custom_args = custom_def
            custom_defn = self.get_parsed(custom_id)
            assert isinstance(custom_defn, CheckableGenericDef)
            assert len(custom_args) == len(custom_defn.params)
            self.register_generic_use(custom_defn, custom_args)
            added = True
        return added

    def _resolve_modified_call(
        self, callee: MonoDefId, modifier_ctx: ModifierContext
    ) -> tuple[MonoDefId, ConcreteCustomUse | None]:
        """Returns the resolved callee and its custom use, if one is required."""
        kind = modifier_ctx.kind_required()
        if kind is None:
            # No modification required
            return callee, None

        callee_id, callee_inst = callee
        if not is_concrete_inst(callee_inst):
            # Callee is not concrete, we cannot resolve the call yet.
            return callee, None

        custom_id = DEF_STORE.custom_modified_defs.get(callee_id, {}).get(kind)
        if custom_id is None:
            # No custom definition available for this kind of modification
            return callee, None

        control_count = None
        custom_args = callee_inst
        if kind.takes_controls:
            try:
                control_count = modifier_ctx.concrete_control_count()
            except ValueError:
                # Control count is not concrete, we cannot resolve the call yet.
                return callee, None
            custom_args = (
                *callee_inst,
                ConstArg(ConstValue(nat_type(), control_count)),
            )

        custom_def = (custom_id, custom_args)
        return custom_def, ConcreteCustomUse(
            unmodified_callee=callee,
            custom_def=custom_def,
            kind=kind,
            control_count=control_count,
        )

    @pretty_errors
    def compile_single(self, id: DefId) -> ModulePointer:
        """Top-level function to begin compilation of a definition into a Hugr module.

        This is the function that is invoked by e.g. `<guppy-definition>.compile`.
        """
        pointer, [compiled_def] = self._compile(
            [id], f"compile {DEF_STORE.raw_defs[id]}"
        )

        if (
            isinstance(compiled_def, CompiledHugrNodeDef)
            and isinstance(compiled_def, CompiledCallableDef)
            and not isinstance(pointer.module[compiled_def.hugr_node].op, FuncDecl)
        ):
            # if compiling a region set it as the HUGR entrypoint can be
            # loosened after https://github.com/quantinuum/hugr/issues/2501 is fixed
            pointer.module.entrypoint = compiled_def.hugr_node

        return pointer

    @pretty_errors
    def compile(self, def_ids: list[DefId], *, reset: bool = True) -> ModulePointer:
        """Top-level function to begin compilation of a range of definitions into a Hugr
        module.

        This is the function that is invoked by e.g. `<guppy-library>.compile`.
        """
        return self._compile(def_ids, context="call compile()", reset=reset)[0]

    def _compile(
        self, def_ids: list[DefId], context: str, *, reset: bool = True
    ) -> tuple[ModulePointer, list[CompiledDef]]:
        # Avoid side-effects of checking if we are not going to compile.
        self.assert_stage(CompilationStage.NONE, context)
        self.check(def_ids, reset=reset)
        assert self._stage == CompilationStage.NONE, "Checking should have reset stage"
        with self._in_stage(CompilationStage.COMPILE):
            return self._compile_impl(def_ids)

    def _compile_impl(
        self, def_ids: list[DefId]
    ) -> tuple[ModulePointer, list[CompiledDef]]:
        callgraph = CallGraph(self.call_graph)
        effects = compute_effects(callgraph, self.func_effects)

        # Prepare Hugr for this module
        graph = hf.Module()
        graph.metadata["name"] = "__main__"  # entrypoint metadata

        # Lower definitions to Hugr
        from guppylang_internals.compiler.core import CompilerContext

        # Set up string tables for metadata serialization. We know that the first entry
        # in the table is always the file containing the Hugr entrypoint.
        frame = get_calling_frame()
        filename = frame.f_code.co_filename

        ctx = CompilerContext(
            graph,
            set(def_ids),
            effects,
            self.custom_uses_by_mono_def,
            StringTable(),
        )
        requested_defs = []
        for def_id in def_ids:
            check_entry_point_non_generic(self.get_parsed(def_id))
            requested_defs.append(ctx.build_compiled_def(def_id, type_args=None))
        ctx.iterate_worklist()
        self.compiled = ctx.compiled

        # Add debug info about the module to the root node
        if debug_mode_enabled():
            module_info = DICompileUnit(
                directory=Path.cwd().as_uri(),
                # We know this file is always the first entry in the file table.
                filename=ctx.metadata_file_table.get_index(filename),
                file_table=ctx.metadata_file_table.table,
            )
            graph.hugr[graph.hugr.module_root].metadata[HugrDebugInfo] = module_info

        # Build resolve registry: start with cached base, add any additional
        if self.additional_extensions:
            from copy import deepcopy

            resolve_registry = deepcopy(self._get_base_resolve_registry())
            for ext in self.additional_extensions:
                resolve_registry.register(ext)
        else:
            resolve_registry = self._get_base_resolve_registry()

        # Compute used extensions dynamically from the HUGR.
        used_extensions_result = graph.hugr.used_extensions(
            resolve_from=resolve_registry
        )

        # Set metadata for used extensions
        used_exts_meta = [
            ExtensionDesc(name=ext.name, version=ext.version)
            for ext in used_extensions_result.used_extensions.extensions
        ]
        # Add unresolved extensions as well, but we only have the names
        used_exts_meta.extend(
            [
                # TODO: Remove dummy version once optional in Hugr.
                ExtensionDesc(
                    name=ext_name, version=Version(major=0, prerelease="unknown")
                )
                for ext_name in used_extensions_result.unresolved_extensions
            ]
        )
        root_metadata = graph.hugr[graph.hugr.module_root].metadata
        root_metadata[HugrUsedExtensions] = used_exts_meta
        root_metadata[HugrGenerator] = GeneratorDesc(
            name="guppylang",
            version=Version.parse(
                guppylang_internals.__version__, optional_minor_and_patch=True
            ),
        )
        # Package all non-standard extensions used in the hugr.
        # Standard hugr extensions are universally available and don't need bundling.
        std_ext_names = hugr.std._std_extensions()
        packaged_extensions = [
            ext
            for ext in used_extensions_result.used_extensions.extensions
            if ext.name not in std_ext_names
        ]
        return (
            ModulePointer(
                Package(modules=[graph.hugr], extensions=packaged_extensions), 0
            ),
            requested_defs,
        )


@dataclass(frozen=True)
class EntryMonomorphizeError(Error):
    title: ClassVar[str] = "Invalid entry point"
    span_label: ClassVar[str] = (
        "{thing} is not a valid compilation entry point since the value{plural_s} of "
        "its generic parameter{plural_s} {params_str} {is_are} not known"
    )
    thing: str
    params: Sequence[Parameter]

    @property
    def plural_s(self) -> str:
        return "s" if len(self.params) > 1 else ""

    @property
    def is_are(self) -> str:
        return "are" if len(self.params) > 1 else "is"

    @property
    def params_str(self) -> str:
        return ", ".join(f"`{p.name}`" for p in self.params)


class CompilationStageError(InternalGuppyError):
    """Raised when the CompilationEngine is requested to do some operation
    during a stage in which the operation cannot be performed"""

    def __init__(
        self,
        context: str,
        *,
        actual_stage: CompilationStage,
        expected_stage: CompilationStage,
    ) -> None:
        super().__init__(
            f"Can only {context} during `{expected_stage}`, not `{actual_stage}`"
        )


@dataclass(frozen=True)
class EntryCheckMonomorphizeError(Error):
    title: ClassVar[str] = "Invalid check point"
    span_label: ClassVar[str] = (
        "{thing} can only be checked if the value{plural_s} of its generic "
        "parameter{plural_s} {params_str} {is_are} known"
    )
    defn: CheckableGenericDef

    @property
    def thing(self) -> str:
        return self.defn.to_caps_str()

    @property
    def plural_s(self) -> str:
        return "s" if len(self.defn.params) > 1 else ""

    @property
    def is_are(self) -> str:
        return "are" if len(self.defn.params) > 1 else "is"

    @property
    def params_str(self) -> str:
        return ", ".join(f"`{p.name}`" for p in self.defn.params)


def check_entry_point_non_generic(defn: ParsedDef) -> None:
    """Checks if the given definition is a valid compilation entry-point.

    In particular, ensures that the definition doesn't depend on generic parameters.
    """
    if isinstance(defn, CheckableGenericDef) and defn.params:
        assert defn.defined_at is not None
        raise GuppyError(
            EntryMonomorphizeError(defn.defined_at, defn.to_caps_str(), defn.params)
        )


def _check_generic_def_instantiation(
    defn: CheckableGenericDef, mono_args: Inst, globals: "Globals"
) -> CheckedDef:
    try:
        return defn.check(mono_args, globals)
    except GuppyError as err:
        # If this is an error arising from the initial parametric check where
        # parameters are treated as opaque values, then we can just report the
        # error as is. However, if the error only shows up once we check a
        # concrete monomorphic instantiation, then we should also report this
        # instantiation in the error message to give some additional context.
        if instantiation_context_is_useful_for_error(mono_args):
            err.error.add_sub_diagnostic(MonoArgsNote(None, defn.params, mono_args))
        raise


def instantiation_context_is_useful_for_error(mono_args: Inst) -> bool:
    """Checks if the given instantiation should be attached as context to an error.

    This is the case if the `mono_args` instantiation is an actual monomorphic
    instantiation instead of an opaque one used for the initial parametric check.

    Empty instantiations are never included as context.
    """
    for arg in mono_args:
        match arg:
            case TypeArg(ty=BoundTypeVar()):
                return False
            case ConstArg(const=BoundConstVar()):
                return False
            case _:
                return True
    return False


@dataclass(frozen=True)
class CustomModifiedDefSignatureError(Error):
    title: ClassVar[str] = (
        "Incompatible signature for custom `{implementation}` implementation"
    )
    span_label: ClassVar[str] = (
        "Expected signature `{expected_signature}`, got `{actual_signature}`"
    )
    implementation: str
    expected_signature: str
    actual_signature: FunctionType

    class DaggeredNote(Note):
        message: ClassVar[str] = (
            "A custom `daggered` implementation must have the same signature as its "
            "parent function."
        )

    class ControlledNote(Note):
        message: ClassVar[str] = (
            "A custom `{implementation}` implementation must have its parent "
            "function's signature followed by an `array[qubit, n]` input containing "
            "the control qubits."
        )


def _check_modified_def_signature(
    parsed_modified_def: "ParsedFunctionDef", parent_ty: FunctionType
) -> None:
    """Checks that a custom modified definition has a signature compatible with its
    parent:
    - `daggered`: must have exactly the same signature as the parent.
    - `controlled` / `ctrl_daggered`: must have the parent's signature extended
      with a `array[qubit, n]` input holding the control qubits.
    """
    if parsed_modified_def.name == CALL_DAGGERED_METHOD:
        daggered_ty = parsed_modified_def.ty
        if unify(parent_ty, daggered_ty, {}) is None:
            err = CustomModifiedDefSignatureError(
                parsed_modified_def.defined_at,
                implementation=CALL_DAGGERED_METHOD,
                expected_signature=f"{parent_ty}",
                actual_signature=daggered_ty,
            )
            err.add_sub_diagnostic(CustomModifiedDefSignatureError.DaggeredNote(None))
            raise GuppyError(err)
    elif (
        parsed_modified_def.name == CALL_CONTROLLED_METHOD
        or parsed_modified_def.name == CALL_CTRL_DAGGERED_METHOD
    ):
        _check_controlled_def_signature(
            parsed_modified_def.ty,
            parent_ty,
            parsed_modified_def.defined_at,
            parsed_modified_def.name,
        )
    else:
        raise InternalGuppyError(
            f"Unexpected modified def name: {parsed_modified_def.name}"
        )


def _check_controlled_def_signature(
    modified_ty: FunctionType,
    parent_ty: FunctionType,
    defined_at: ast.FunctionDef,
    implementation: str,
) -> None:
    first_part_ty = FunctionType(
        # last input must be the array of control qubits
        modified_ty.inputs[:-1],
        modified_ty.output,
        # last param must be parameter for the number of control qubits
        modified_ty.params[:-1],
        modified_ty.comptime_args,
        modified_ty.unitary_flags,
    )
    invalid_signature = (
        len(modified_ty.inputs) != len(parent_ty.inputs) + 1
        or len(modified_ty.params) != len(parent_ty.params) + 1
        or unify(first_part_ty, parent_ty, {}) is None
    )
    if not invalid_signature:
        last_input_ty = modified_ty.inputs[-1].ty
        last_param = modified_ty.params[-1]
        invalid_signature = (
            not is_array_type(last_input_ty)
            or not is_qubit_ty(get_element_type(last_input_ty))
            or modified_ty.inputs[-1].flags != InputFlags.Inout
            or not isinstance(last_param, ConstParam)
            or get_array_length(last_input_ty)
            != BoundConstVar(last_param.ty, last_param.name, last_param.idx)
        )

    if invalid_signature:
        control_param = ConstParam(len(parent_ty.params), "n", nat_type())
        control_input = FuncInput(
            array_type(
                qubit_ty(),
                BoundConstVar(control_param.ty, control_param.name, control_param.idx),
            ),
            InputFlags.Inout,
            "_controls" if parent_ty.input_names is not None else None,
        )
        expected_signature = str(
            FunctionType(
                [*parent_ty.inputs, control_input],
                parent_ty.output,
                [*parent_ty.params, control_param],
                parent_ty.comptime_args,
                parent_ty.unitary_flags,
            )
        )
        err = CustomModifiedDefSignatureError(
            defined_at,
            implementation=implementation,
            expected_signature=expected_signature,
            actual_signature=modified_ty,
        )
        err.add_sub_diagnostic(CustomModifiedDefSignatureError.ControlledNote(None))
        raise GuppyError(err)


ENGINE: CompilationEngine = CompilationEngine()
