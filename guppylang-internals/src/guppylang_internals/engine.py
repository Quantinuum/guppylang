from collections import defaultdict
from pathlib import Path
from types import FrameType
from typing import TYPE_CHECKING, cast

import hugr
import hugr.build.function as hf
from hugr import ops
from hugr.debug_info import DICompileUnit
from hugr.envelope import ExtensionDesc, GeneratorDesc
from hugr.ext import Extension, ExtensionRegistry
from hugr.metadata import HugrDebugInfo, HugrGenerator, HugrUsedExtensions
from hugr.package import ModulePointer, Package
from semver import Version
from typing_extensions import assert_never, deprecated

import guppylang_internals
from guppylang_internals.debug_mode import debug_mode_enabled
from guppylang_internals.definition.common import (
    CheckableDef,
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
    CompiledCallableDef,
    CompiledHugrNodeDef,
)
from guppylang_internals.error import (
    pretty_errors,
)
from guppylang_internals.metadata.debug_info_util import (
    StringTable,
)
from guppylang_internals.span import SourceMap
from guppylang_internals.tracing.util import get_calling_frame
from guppylang_internals.tys.builtin import (
    array_type_def,
    bool_type_def,
    callable_type_def,
    float_type_def,
    frozenarray_type_def,
    int_type_def,
    list_type_def,
    nat_type_def,
    none_type_def,
    option_type_def,
    self_type_def,
    sized_iter_type_def,
    string_type_def,
    tuple_type_def,
)
from guppylang_internals.tys.ty import (
    BoundTypeVar,
    EnumType,
    ExistentialTypeVar,
    FunctionType,
    NoneType,
    NumericType,
    OpaqueType,
    StructType,
    TupleType,
    Type,
)

if TYPE_CHECKING:
    from guppylang_internals.compiler.core import MonoDefId

BUILTIN_DEFS_LIST: list[RawDef] = [
    callable_type_def,
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
]

BUILTIN_DEFS = {defn.name: defn for defn in BUILTIN_DEFS_LIST}


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

    def __init__(self) -> None:
        self.raw_defs = {defn.id: defn for defn in BUILTIN_DEFS_LIST}
        self.type_members = defaultdict(dict)
        self.type_member_parents = {}
        self.frames = {}
        self.sources = SourceMap()
        self.wasm_functions = {}

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


DEF_STORE: DefinitionStore = DefinitionStore()


class CompilationEngine:
    """Main compiler driver handling checking and compiling of definitions.

    The engine maintains a worklist of definitions that still need to be checked and
    makes sure that all dependencies are compiled.

    See `ENGINE` for the singleton instance of this class.
    """

    parsed: dict[DefId, ParsedDef]
    checked: dict[DefId, CheckedDef]
    compiled: dict["MonoDefId", CompiledDef]
    additional_extensions: list[Extension]

    types_to_check_worklist: dict[DefId, ParsedDef]
    to_check_worklist: dict[DefId, ParsedDef]

    # Cached compilation infrastructure (lazy-initialized, program-independent)
    _base_resolve_registry: ExtensionRegistry | None = None

    def __init__(self) -> None:
        """Resets the compilation cache."""
        self.reset()
        self.additional_extensions = []

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
        self.types_to_check_worklist = {}

    @pretty_errors
    @deprecated(
        "Extensions are included automatically when used. "
        "Manual registration is no longer necessary."
    )
    def register_extension(self, extension: Extension) -> None:
        if extension not in self.additional_extensions:
            self.additional_extensions.append(extension)

    @pretty_errors
    def get_parsed(self, id: DefId) -> ParsedDef:
        """Look up the parsed version of a definition by its id.

        Parses the definition if it hasn't been parsed yet. Also makes sure that the
        definition will be checked and compiled later on.
        """
        from guppylang_internals.checker.core import Globals

        if id in self.parsed:
            return self.parsed[id]
        defn = DEF_STORE.raw_defs[id]
        if isinstance(defn, ParsableDef):
            defn = defn.parse(Globals(DEF_STORE.frames[defn.id]), DEF_STORE.sources)

        self.parsed[id] = defn
        if isinstance(defn, TypeDef):
            self.types_to_check_worklist[id] = defn
        else:
            self.to_check_worklist[id] = defn
        return defn

    @pretty_errors
    def get_checked(self, id: DefId) -> CheckedDef:
        """Look up the checked version of a definition by its id.

        Parses and checks the definition if it hasn't been parsed/checked yet. Also
        makes sure that the definition will be compiled to Hugr later on.
        """
        from guppylang_internals.checker.core import Globals

        if id in self.checked:
            return self.checked[id]
        defn = self.get_parsed(id)
        if isinstance(defn, CheckableDef):
            defn = defn.check(Globals(DEF_STORE.frames[defn.id]))
        self.checked[id] = defn

        from guppylang_internals.definition.enum import CheckedEnumDef
        from guppylang_internals.definition.struct import CheckedStructDef

        if isinstance(defn, CheckedStructDef | CheckedEnumDef):
            for method_def in defn.generated_methods():
                DEF_STORE.register_def(method_def, DEF_STORE.frames[id])
                DEF_STORE.register_type_member(defn.id, method_def.name, method_def.id)

        return defn

    def get_instance_func(self, ty: Type | TypeDef, name: str) -> CallableDef | None:
        """Looks up an instance function with a given name for a type.

        Returns `None` if the name doesn't exist or isn't a function.
        """
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
                type_defn = callable_type_def
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

        type_defn = cast("TypeDef", ENGINE.get_checked(type_defn.id))
        if (
            type_defn.id in DEF_STORE.type_members
            and name in DEF_STORE.type_members[type_defn.id]
        ):
            def_id = DEF_STORE.type_members[type_defn.id][name]
            defn = ENGINE.get_parsed(def_id)
            if isinstance(defn, CallableDef):
                return defn
        return None

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

        for def_id in def_ids:
            self.to_check_worklist[def_id] = self.get_parsed(def_id)

        while self.types_to_check_worklist or self.to_check_worklist:
            # Types need to be checked first. This is because parsing e.g. a function
            # definition requires instantiating the types in its signature which can
            # only be done if the types have already been checked.
            if self.types_to_check_worklist:
                id, _ = self.types_to_check_worklist.popitem()
            else:
                id, _ = self.to_check_worklist.popitem()
            self.checked[id] = self.get_checked(id)

    @pretty_errors
    def compile_single(self, id: DefId) -> ModulePointer:
        """Top-level function to begin compilation of a definition into a Hugr module.

        This is the function that is invoked by e.g. `<guppy-definition>.compile`.
        """
        pointer, [compiled_def] = self._compile([id])

        if (
            isinstance(compiled_def, CompiledHugrNodeDef)
            and isinstance(compiled_def, CompiledCallableDef)
            and not isinstance(pointer.module[compiled_def.hugr_node].op, ops.FuncDecl)
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
        return self._compile(def_ids, reset=reset)[0]

    def _compile(
        self, def_ids: list[DefId], *, reset: bool = True
    ) -> tuple[ModulePointer, list[CompiledDef]]:
        self.check(def_ids, reset=reset)

        # Prepare Hugr for this module
        graph = hf.Module()
        graph.metadata["name"] = "__main__"  # entrypoint metadata

        # Lower definitions to Hugr
        from guppylang_internals.compiler.core import CompilerContext

        # Set up string tables for metadata serialization. We know that the first entry
        # in the table is always the file containing the Hugr entrypoint.
        frame = get_calling_frame()
        assert frame is not None
        filename = frame.f_code.co_filename

        ctx = CompilerContext(graph, set(def_ids), StringTable())
        requested_defs = [ctx.compile(self.checked[def_id]) for def_id in def_ids]
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
            graph.hugr.module_root.metadata[HugrDebugInfo] = module_info

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
        graph.hugr.module_root.metadata[HugrUsedExtensions] = used_exts_meta
        graph.hugr.module_root.metadata[HugrGenerator] = GeneratorDesc(
            name="guppylang", version=Version.parse(guppylang_internals.__version__)
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


ENGINE: CompilationEngine = CompilationEngine()
