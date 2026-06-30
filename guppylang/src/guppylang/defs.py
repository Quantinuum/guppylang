"""Definition objects that are being exposed to users.

These are the objects returned by the `@guppy` decorator. They should not be confused
with the compiler-internal definition objects in the `definitions` module.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Generic, ParamSpec, TypeVar, cast

import guppylang_internals
from guppylang_internals.definition.declaration import RawFunctionDecl
from guppylang_internals.definition.enum import CheckedEnumDef
from guppylang_internals.definition.function import RawFunctionDef
from guppylang_internals.definition.value import CompiledCallableDef
from guppylang_internals.diagnostic import Error, Note
from guppylang_internals.engine import DEF_STORE, ENGINE
from guppylang_internals.error import GuppyError, pretty_errors
from guppylang_internals.span import Span, to_span
from guppylang_internals.tracing.object import TracingDefMixin
from guppylang_internals.tracing.util import hide_trace
from hugr.envelope import GeneratorDesc
from hugr.hugr import Hugr
from hugr.metadata import HugrGenerator
from hugr.package import Package
from semver import Version

import guppylang
from guppylang.emulator import EmulatorBuilder, EmulatorInstance
from guppylang.emulator._args import (
    EntrypointArgSpec,
    unsupported_arg_reason,
    wrap_entrypoint_with_args,
)
from guppylang.emulator.builder import Platform
from guppylang.emulator.exceptions import EmulatorBuildError

if TYPE_CHECKING:
    import ast

__all__ = (
    "GuppyDefinition",
    "GuppyEnumDefinition",
    "GuppyFunctionDefinition",
    "GuppyTypeVarDefinition",
)


P = ParamSpec("P")
Out = TypeVar("Out")


def _update_generator_metadata(hugr: Hugr[Any]) -> None:
    """Update the generator metadata of a Hugr to be
    guppylang rather than just internals."""
    hugr.module_root.metadata[HugrGenerator] = GeneratorDesc(
        name=f"guppylang (guppylang-internals-v{guppylang_internals.__version__})",
        version=Version.parse(guppylang.__version__),
    )


@dataclass(frozen=True)
class EntrypointArgsError(Error):
    title: ClassVar[str] = "Entrypoint function has arguments"
    span_label: ClassVar[str] = (
        "Entrypoint function must have no input parameters, found ({input_names})."
    )
    args: Sequence[str]

    @dataclass(frozen=True)
    class AlternateHint(Note):
        message: ClassVar[str] = (
            "If the function is not an execution entrypoint,"
            " consider using `{function_name}.compile_function()`"
        )
        function_name: str

    @property
    def input_names(self) -> str:
        """Returns a comma-separated list of input names."""
        return ", ".join(f"`{x}`" for x in self.args)


@dataclass(frozen=True)
class UnsupportedEntrypointArgError(Error):
    title: ClassVar[str] = "Unsupported entrypoint argument type"
    span_label: ClassVar[str] = "{reason}"
    reason: str


@dataclass(frozen=True)
class GuppyDefinition(TracingDefMixin):
    """A general Guppy definition."""

    def compile(self) -> Package:
        """Compile a Guppy definition to HUGR."""
        package: Package = ENGINE.compile_single(self.id).package
        for mod in package.modules:
            _update_generator_metadata(mod)
        return package

    def check(self) -> None:
        """Type-check a Guppy definition."""
        return ENGINE.check_single(self.id)


@dataclass(frozen=True)
class GuppyEnumDefinition(GuppyDefinition):
    """A Guppy enum definition."""

    @hide_trace
    def __getattr__(self, name: str) -> Any:
        # Handle attribute access when calling an enum variant constructor, like
        # `Enum.VariantA()`. In all other cases, we should not try create a new
        # attribute, so we directly raise the error.
        defn = ENGINE.get_checked(self.wrapped.id, mono_args=())
        assert isinstance(defn, CheckedEnumDef)
        if (
            # We can only access the variants of the enum from the enum class,
            # not methods
            name in defn.variants
            and defn.id in DEF_STORE.type_members
            and name in DEF_STORE.type_members[defn.id]
        ):
            member_def = DEF_STORE.raw_defs[DEF_STORE.type_members[defn.id][name]]
            return TracingDefMixin(member_def)
        raise AttributeError(
            f"{defn.description.capitalize()} `{defn.name}` has no attribute `{name}`"
        )


@dataclass(frozen=True)
class GuppyFunctionDefinition(GuppyDefinition, Generic[P, Out]):
    """A Guppy function definition."""

    @hide_trace
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Out:
        return cast("Out", super().__call__(*args, **kwargs))

    def emulator(
        self,
        n_qubits: int | None = None,
        builder: EmulatorBuilder | None = None,
        libs: list[Package] | None = None,
        platform: Platform = "helios",
    ) -> EmulatorInstance:
        """Compile this function for emulation with the selene-sim emulator.

        Compiles the function to a HUGR package and builds it using the provided
        `EmulatorBuilder` configuration or a default one.

        See :py:mod:`guppylang.emulator` for more details on the emulator.

        Args:
            n_qubits: The number of qubits to allocate for the function. If it is not
            provided, the function has to declare the maximum number of qubits it needs
            in the decorator, e.g. `@guppy(max_qubits=5)`.
            builder: An optional `EmulatorBuilder` to use for building the emulator
            instance. If not provided, the default `EmulatorBuilder` will be used.
            libs: An optional list of additional HUGR packages to link with the compiled
            function. This can be used to provide additional library functions that the
            function being compiled depends on.
            platform: The quantum platform to target. Defaults to ``"helios"``. Set to
            ``"sol"`` to target the Sol QIS. Ignored if an explicit ``builder`` is
            provided (use ``builder.with_platform()`` in that case).

        Returns:
            An `EmulatorInstance` that can be used to run the function in an emulator.
        """
        mod = self.compile_function()

        if libs is not None:
            mod = mod.link(*libs)

        if builder is None:
            builder = EmulatorBuilder().with_platform(platform)

        if arg_specs := self._entrypoint_arg_specs():
            from selene_argreader_plugin import ArgReaderPlugin

            wrap_entrypoint_with_args(mod, [spec.name for spec in arg_specs])
            builder = builder.link_utility(ArgReaderPlugin())

        qubits = n_qubits
        if (
            isinstance(self.wrapped, RawFunctionDef)
            and self.wrapped.metadata is not None
        ):
            hinted_qubits = self.wrapped.metadata.get_max_qubits()
            if qubits is None:
                qubits = hinted_qubits
            elif hinted_qubits is not None and qubits < hinted_qubits:
                raise EmulatorBuildError(
                    ValueError(
                        f"Number of qubits requested ({qubits}) is insufficient to "
                        "cover the maximum number of qubits hinted on the "
                        f"entrypoint ({hinted_qubits})."
                    )
                )

        if qubits is None:
            raise EmulatorBuildError(
                ValueError(
                    "Number of qubits to be used must be specified, either as an "
                    f"argument to `{self.emulator.__name__}` or hinted on the "
                    "entrypoint function using `@guppy(max_qubits=...)`."
                )
            )

        return builder.build(mod, n_qubits=qubits, arg_specs=arg_specs)

    @pretty_errors
    def _entrypoint_arg_specs(self) -> tuple[EntrypointArgSpec, ...]:
        """Validate and collect the runtime argument schema of the entrypoint.

        Returns an empty tuple if the entrypoint takes no arguments. Raises a
        `GuppyError` if any argument has an unsupported type.
        """
        result = self._compiled_entrypoint_with_inputs()
        if result is None:
            return ()

        compiled_def, defined_at = result
        specs: list[EntrypointArgSpec] = []
        for name, inp, ast_arg in zip(
            compiled_def.ty.input_names or [],
            compiled_def.ty.inputs,
            defined_at.args.args,
            strict=True,
        ):
            if (reason := unsupported_arg_reason(inp.ty)) is not None:
                raise GuppyError(
                    UnsupportedEntrypointArgError(span=to_span(ast_arg), reason=reason)
                )
            specs.append(EntrypointArgSpec(name=name, ty=inp.ty))
        return tuple(specs)

    def _compiled_entrypoint_with_inputs(
        self,
    ) -> tuple[CompiledCallableDef, "ast.FunctionDef"] | None:
        """Return the compiled entrypoint and its AST node if it has inputs, else
        None.
        """
        # Entrypoints cannot be polymorphic; we always look up the monomorphized id.
        compiled_def = ENGINE.compiled.get((self.id, ()))
        if (
            isinstance(compiled_def, CompiledCallableDef)
            and len(compiled_def.ty.inputs) > 0
        ):
            return compiled_def, cast("ast.FunctionDef", compiled_def.defined_at)
        return None

    def compile(self) -> Package:
        """
        Compiles an execution entrypoint function definition to a HUGR package

        Equivalent to :py:meth:`GuppyDefinition.compile_entrypoint`.


        Returns:
            Package: The compiled package object.
        Raises:
            GuppyError: If the entrypoint has arguments.
        """

        return self.compile_entrypoint()

    @pretty_errors
    def compile_entrypoint(self) -> Package:
        """
        Compiles an execution entrypoint function definition to a HUGR package

        Returns:
            Package: The compiled package object.
        Raises:
            GuppyError: If the entrypoint has arguments.
        """

        pack = self.compile_function()
        if (result := self._compiled_entrypoint_with_inputs()) is not None:
            compiled_def, defined_at = result
            start = to_span(defined_at.args.args[0])
            end = to_span(defined_at.args.args[-1])
            span = Span(start=start.start, end=end.end)
            raise GuppyError(
                EntrypointArgsError(
                    span=span,
                    args=compiled_def.ty.input_names or "",
                ).add_sub_diagnostic(
                    EntrypointArgsError.AlternateHint(
                        None, function_name=defined_at.name
                    )
                )
            )
        return pack

    def compile_function(self) -> Package:
        """Compile a Guppy function definition to HUGR.


        Returns:
            Package: The compiled package object.
        """
        return super().compile()

    @property
    def is_decl(self) -> bool:
        """Whether this function definition is a declaration (i.e. has no body)."""
        return isinstance(self.wrapped, RawFunctionDecl)


@dataclass(frozen=True)
class GuppyTypeVarDefinition(GuppyDefinition):
    """Definition of a Guppy type variable."""

    # For type variables, we need a `GuppyDefinition` subclass that answers 'yes' to an
    # instance check on `typing.TypeVar`. This hack is needed since `typing.Generic[T]`
    # has a runtime check that enforces that the passed `T` is actually a `TypeVar`.

    __class__: ClassVar[type] = TypeVar

    _ty_var: TypeVar

    def __eq__(self, other: object) -> bool:
        # We need to compare as equal to an equivalent regular type var
        if isinstance(other, TypeVar):
            return self._ty_var == other
        return object.__eq__(self, other)

    def __getattr__(self, name: str) -> Any:
        # Pretend to be a `TypeVar` by providing all of its attributes
        if hasattr(self._ty_var, name):
            return getattr(self._ty_var, name)
        return object.__getattribute__(self, name)
