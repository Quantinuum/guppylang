from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from types import FrameType
from typing import ClassVar

import hugr.build.function as hf
import hugr.std.collections.array
import hugr.std.float
import hugr.std.int
import hugr.std.logic
import hugr.std.prelude
from hugr import ops
from hugr.ext import Extension
from hugr.package import ModulePointer, Package

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
    CompiledCallableDef,
    CompiledHugrNodeDef,
)
from guppylang_internals.diagnostic import Error
from guppylang_internals.error import GuppyError, pretty_errors
from guppylang_internals.span import SourceMap
from guppylang_internals.tys.arg import Argument
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
from guppylang_internals.tys.param import Parameter
from guppylang_internals.tys.subst import Inst
from guppylang_internals.tys.ty import FunctionType

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


#: Monomorphic instantiation of the generic parameters of definitions.
#:
#: This is similar to the `Inst` type, however we use a tuple here since the
#: instantiation is required to be hashable.
MonoArgs = tuple[Argument, ...]

#: Identifier for a monomorphized version of a definition.
#:
#: Kinds of definitions that are never generic (e.g. constant definitions) and
#: definitions without generic parameters (e.g. a non-generic function definition) are
#: registered with an empty tuple () as `MonoArgs`.
MonoDefId = tuple[DefId, MonoArgs]


class CoreMetadataKeys(Enum):
    """Core HUGR metadata keys used by Guppy."""

    USED_EXTENSIONS = "core.used_extensions"
    GENERATOR = "core.generator"


class DefinitionStore:
    """Storage class holding references to all Guppy definitions created in the current
    interpreter session.

    See `DEF_STORE` for the singleton instance of this class.
    """

    raw_defs: dict[DefId, RawDef]
    impls: defaultdict[DefId, dict[str, DefId]]
    impl_parents: dict[DefId, DefId]
    wasm_functions: dict[DefId, FunctionType]
    frames: dict[DefId, FrameType]
    sources: SourceMap

    def __init__(self) -> None:
        self.raw_defs = {defn.id: defn for defn in BUILTIN_DEFS_LIST}
        self.impls = defaultdict(dict)
        self.impl_parents = {}
        self.frames = {}
        self.sources = SourceMap()
        self.wasm_functions = {}

    def register_def(self, defn: RawDef, frame: FrameType | None) -> None:
        self.raw_defs[defn.id] = defn
        if frame:
            self.frames[defn.id] = frame

    def register_impl(self, ty_id: DefId, name: str, impl_id: DefId) -> None:
        assert impl_id not in self.impl_parents, "Already an impl"
        self.impls[ty_id][name] = impl_id
        self.impl_parents[impl_id] = ty_id
        # Update the frame of the definition to the frame of the defining class
        if impl_id in self.frames:
            frame = self.frames[impl_id].f_back
            if frame:
                self.frames[impl_id] = frame
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
                    self.frames[impl_id] = frame

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
    checked: dict["MonoDefId", CheckedDef]
    compiled: dict["MonoDefId", CompiledDef]
    additional_extensions: list[Extension]

    types_to_check_worklist: dict[DefId, ParsedDef]
    to_check_worklist: dict["MonoDefId", ParsedDef]

    to_compile_worklist: dict["MonoDefId", CheckedDef]

    def __init__(self) -> None:
        """Resets the compilation cache."""
        self.reset()
        self.additional_extensions = []

    def reset(self) -> None:
        """Resets the compilation cache."""
        self.parsed = {}
        self.checked = {}
        self.compiled = {}
        self.to_check_worklist = {}
        self.types_to_check_worklist = {}

    @pretty_errors
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
            defn = defn.parse(Globals(defn.id), DEF_STORE.sources)
        self.parsed[id] = defn
        if isinstance(defn, TypeDef):
            self.types_to_check_worklist[id] = defn
        elif isinstance(defn, CheckableDef):
            self.to_check_worklist[id, ()] = defn
        # If `defn` is a `CheckableGenericDef`, we can't add it to the worklist yet
        # since we don't know the generic instantiation yet. It will be added when
        # we're checking a use of the definition (e.g. a call). See for example
        # `ParsedFunctionDef.check_call`.
        return defn

    @pretty_errors
    def get_checked(self, id: DefId, mono_args: MonoArgs | None) -> CheckedDef:
        """Look up the checked version of a definition by its id.

        Parses and checks the definition if it hasn't been parsed/checked yet. Also
        makes sure that the definition will be compiled to Hugr later on.
        """
        from guppylang_internals.checker.core import Globals

        mono_args = mono_args or ()
        if (id, mono_args) in self.checked:
            return self.checked[id, mono_args]
        defn = self.get_parsed(id)
        if isinstance(defn, CheckableDef):
            defn = defn.check(Globals(defn.id))
        elif isinstance(defn, CheckableGenericDef):
            defn = defn.check(mono_args, Globals(defn.id))
        self.checked[id, mono_args] = defn

        from guppylang_internals.definition.struct import CheckedStructDef

        if isinstance(defn, CheckedStructDef):
            for method_def in defn.generated_methods():
                DEF_STORE.register_def(method_def, None)
                DEF_STORE.register_impl(defn.id, method_def.name, method_def.id)

        return defn

    def register_generic_use(self, defn: CheckableGenericDef, type_args: Inst) -> None:
        """Tells the engine that an instantiation of a generic definition has been
        used.

        Adds the instantiation to the worklist and ensures that it will be checked.
        """
        mono_args = tuple(type_args)
        self.to_check_worklist[defn.id, mono_args] = defn

    @pretty_errors
    def check(self, id: DefId) -> None:
        """Top-level function to kick of checking of a definition.

        This is the main driver behind `guppy.check()`.
        """
        # Clear previous compilation cache.
        # TODO: In order to maintain results from the previous `check` call we would
        #  need to store and check if any dependencies have changed.
        self.reset()

        entry_defn = self.get_parsed(id)
        entry_mono_args = check_valid_entry_point(entry_defn)
        self.to_check_worklist[id, entry_mono_args] = entry_defn

        while self.types_to_check_worklist or self.to_check_worklist:
            # Types need to be checked first. This is because parsing e.g. a function
            # definition requires instantiating the types in its signature which can
            # only be done if the types have already been checked.
            if self.types_to_check_worklist:
                id, _ = self.types_to_check_worklist.popitem()
                mono_args: MonoArgs = ()
            else:
                (id, mono_args), _ = self.to_check_worklist.popitem()
            self.checked[id, mono_args] = self.get_checked(id, mono_args)

    @pretty_errors
    def compile(self, id: DefId) -> ModulePointer:
        """Top-level function to kick of Hugr compilation of a definition.

        This is the function that is invoked by `guppy.compile`.
        """
        self.check(id)

        # Prepare Hugr for this module
        graph = hf.Module()
        graph.metadata["name"] = "__main__"  # entrypoint metadata

        # Lower definitions to Hugr
        from guppylang_internals.compiler.core import CompilerContext

        ctx = CompilerContext(graph)
        entry_mono_args = check_valid_entry_point(self.get_parsed(id))
        compiled_def = ctx.compile(self.checked[id, entry_mono_args], entry_mono_args)
        self.compiled = ctx.compiled

        if (
            isinstance(compiled_def, CompiledHugrNodeDef)
            and isinstance(compiled_def, CompiledCallableDef)
            and not isinstance(graph.hugr[compiled_def.hugr_node].op, ops.FuncDecl)
        ):
            # if compiling a region set it as the HUGR entrypoint can be
            # loosened after https://github.com/quantinuum/hugr/issues/2501 is fixed
            graph.hugr.entrypoint = compiled_def.hugr_node

        # TODO: Currently the list of extensions is manually managed by the user.
        #  We should compute this dynamically from the imported dependencies instead.
        #
        # The hugr prelude and std_extensions are implicit.
        from guppylang_internals.std._internal.compiler.tket_exts import TKET_EXTENSIONS

        extensions = [
            *TKET_EXTENSIONS,
            guppylang_internals.compiler.hugr_extension.EXTENSION,
            *self.additional_extensions,
        ]
        # TODO replace with computed extensions after https://github.com/quantinuum/guppylang/issues/550
        all_used_extensions = [
            *extensions,
            hugr.std.prelude.PRELUDE_EXTENSION,
            hugr.std.collections.array.EXTENSION,
            hugr.std.float.FLOAT_OPS_EXTENSION,
            hugr.std.float.FLOAT_TYPES_EXTENSION,
            hugr.std.int.INT_OPS_EXTENSION,
            hugr.std.int.INT_TYPES_EXTENSION,
            hugr.std.logic.EXTENSION,
        ]
        graph.hugr.module_root.metadata[CoreMetadataKeys.USED_EXTENSIONS.value] = [
            {
                "name": ext.name,
                "version": str(ext.version),
            }
            for ext in all_used_extensions
        ]
        graph.hugr.module_root.metadata[CoreMetadataKeys.GENERATOR.value] = {
            "name": "guppylang",
            "version": guppylang_internals.__version__,
        }
        return ModulePointer(Package(modules=[graph.hugr], extensions=extensions), 0)


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


def check_valid_entry_point(defn: ParsedDef) -> MonoArgs:
    """Checks if the given definition is a valid compilation entry-point.

    In particular, ensures that the definition doesn't depend on generic parameters and
    returns the `MonoArgs` key that should be used for further compilation.
    """
    if isinstance(defn, CheckableGenericDef) and defn.params:
        assert defn.defined_at is not None
        description = f"{defn.description.capitalize()} `{defn.name}`"
        raise GuppyError(
            EntryMonomorphizeError(defn.defined_at, description, defn.params)
        )
    return ()


ENGINE: CompilationEngine = CompilationEngine()
