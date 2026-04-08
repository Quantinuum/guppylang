from collections import defaultdict
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from types import FrameType
from typing import ClassVar, cast

import hugr
import hugr.build.function as hf
from hugr import ops
from hugr.envelope import ExtensionDesc, GeneratorDesc
from hugr.ext import Extension, ExtensionRegistry
from hugr.metadata import HugrGenerator, HugrUsedExtensions
from hugr.package import ModulePointer, Package
from semver import Version
from typing_extensions import assert_never, deprecated

import guppylang_internals
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
    CompiledCallableDef,
    CompiledHugrNodeDef,
)
from guppylang_internals.diagnostic import Error, Note
from guppylang_internals.error import (
    GuppyError,
    RequiresMonomorphizationError,
    pretty_errors,
)
from guppylang_internals.span import SourceMap
from guppylang_internals.tys.arg import ConstArg, TypeArg
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
from guppylang_internals.tys.const import BoundConstVar
from guppylang_internals.tys.param import Parameter
from guppylang_internals.tys.printing import TypePrinter
from guppylang_internals.tys.subst import BoundVarFinder, Inst
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


#: Identifier for a monomorphized version of a definition.
#:
#: Kinds of definitions that are never generic (e.g. constant definitions) and
#: definitions without generic parameters (e.g. a non-generic function definition) are
#: registered with an empty tuple () as `Inst`. Otherwise, `Inst` will be the
#: instantiation for the generic parameters for the monomorphized version.
MonoDefId = tuple[DefId, Inst]


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
        self.generic_to_check_worklist = {}
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
        elif isinstance(defn, CheckableDef):
            self.to_check_worklist[id, ()] = defn
        elif isinstance(defn, CheckableGenericDef) and defn.params:
            self.generic_to_check_worklist[id] = defn
        # If `defn` is a `CheckableGenericDef`, we can't add it to the worklist yet
        # since we don't know the generic instantiation yet. It will be added when
        # we're checking a use of the definition (e.g. a call). See for example
        # `ParsedFunctionDef.check_call`.
        return defn

    @pretty_errors
    def get_checked(self, id: DefId, mono_args: Inst) -> CheckedDef:
        """Look up the checked version of a definition by its id.

        Parses and checks the definition if it hasn't been parsed/checked yet. Also
        makes sure that the definition will be compiled to Hugr later on.
        """
        from guppylang_internals.checker.core import Globals

        if (id, mono_args) in self.checked:
            return self.checked[id, mono_args]
        defn = self.get_parsed(id)
        if isinstance(defn, CheckableDef):
            defn = defn.check(Globals(DEF_STORE.frames[defn.id]))
        elif isinstance(defn, CheckableGenericDef):
            try:
                checked_defn = defn.check(mono_args, Globals(DEF_STORE.frames[defn.id]))
            except GuppyError as err:
                # If this is an error arising from the initial parametric check where
                # parameters are treated as opaque values, then we can just report the
                # error as is. However, if the error only shows up once we check a
                # concrete monomorphic instantiation, then we should also report this
                # instantiation in the error message to give some additional context.
                if instantiation_context_is_useful_for_error(mono_args):
                    err.error.add_sub_diagnostic(
                        MonoArgsNote(None, defn.params, mono_args)
                    )
                raise
            defn = checked_defn
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
        finder = BoundVarFinder()
        for arg in type_args:
            arg.visit(finder)
        if not finder.bound_vars:
            self.to_check_worklist[defn.id, type_args] = defn

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

        type_defn = cast("TypeDef", ENGINE.get_checked(type_defn.id, mono_args=()))
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
            entry_defn = self.get_parsed(def_id)
            check_entry_point_non_generic(entry_defn)
            entry_mono_args: Inst = ()
            self.to_check_worklist[def_id, entry_mono_args] = entry_defn

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

        ctx = CompilerContext(graph, set(def_ids))
        requested_defs = []
        for def_id in def_ids:
            check_entry_point_non_generic(self.get_parsed(def_id))
            requested_defs.append(ctx.build_compiled_def(def_id, type_args=None))
        ctx.iterate_worklist()
        self.compiled = ctx.compiled

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


def check_entry_point_non_generic(defn: ParsedDef) -> None:
    """Checks if the given definition is a valid compilation entry-point.

    In particular, ensures that the definition doesn't depend on generic parameters.
    """
    if isinstance(defn, CheckableGenericDef) and defn.params:
        assert defn.defined_at is not None
        description = f"{defn.description.capitalize()} `{defn.name}`"
        raise GuppyError(
            EntryMonomorphizeError(defn.defined_at, description, defn.params)
        )


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


ENGINE: CompilationEngine = CompilationEngine()
