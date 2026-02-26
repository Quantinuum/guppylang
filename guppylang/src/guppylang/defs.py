"""Definition objects that are being exposed to users.

These are the objects returned by the `@guppy` decorator. They should not be confused
with the compiler-internal definition objects in the `definitions` module.
"""

import ast
import importlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, ParamSpec, TypeVar, cast

import guppylang_internals
from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.declaration import CheckedFunctionDecl
from guppylang_internals.definition.function import CheckedFunctionDef, RawFunctionDef
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
from guppylang.emulator.exceptions import EmulatorBuildError

__all__ = (
    "GuppyDefinition",
    "GuppyFunctionDefinition",
    "GuppyLibrary",
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
class GuppyFunctionDefinition(GuppyDefinition, Generic[P, Out]):
    """A Guppy function definition."""

    @hide_trace
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Out:
        return cast("Out", super().__call__(*args, **kwargs))

    def emulator(
        self, n_qubits: int | None = None, builder: EmulatorBuilder | None = None
    ) -> EmulatorInstance:
        """Compile this function for emulation with the selene-sim emulator.

        Calls `compile()` to get the HUGR package and then builds it using the
        provided `EmulatorBuilder` configuration or a default one.

        See :py:mod:`guppylang.emulator` for more details on the emulator.


        Args:
            n_qubits: The number of qubits to allocate for the function. If it is not
            provided, the function has to declare the maximum number of qubits it needs
            in the decorator, e.g. `@guppy(max_qubits=5)`.
            builder: An optional `EmulatorBuilder` to use for building the emulator
            instance. If not provided, the default `EmulatorBuilder` will be used.

        Returns:
            An `EmulatorInstance` that can be used to run the function in an emulator.
        """
        mod = self.compile()

        builder = builder or EmulatorBuilder()
        qubits = n_qubits
        if (
            isinstance(self.wrapped, RawFunctionDef)
            and self.wrapped.metadata is not None
        ):
            hinted_qubits = self.wrapped.metadata.max_qubits.value
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

        return builder.build(mod, n_qubits=qubits)

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
        # entrypoint cannot be polymorphic
        monomorphized_id = (self.id, ())
        compiled_def = ENGINE.compiled.get(monomorphized_id)
        if (
            isinstance(compiled_def, CompiledCallableDef)
            and len(compiled_def.ty.inputs) > 0
        ):
            # Check if the entrypoint has arguments
            defined_at = cast("ast.FunctionDef", compiled_def.defined_at)
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


@dataclass(frozen=True)
class GuppyLibrary:
    members: list[DefId]

    def member_ids(self) -> Sequence[DefId]:
        """Returns the definition IDs of the members of this library."""
        return self.members

    def compile(self) -> Package:
        """Compile a Guppy definition to HUGR."""
        pointer = ENGINE.compile(self.members)
        for mod in pointer.package.modules:
            _update_generator_metadata(mod)
        return pointer.package

    def check(self) -> None:
        """Type-check all definitions Guppy definition."""
        ENGINE.check(self.members)

    def stubs(self) -> dict[str, str]:
        stub_asts_by_module: dict[str, list[ast.stmt]] = {}
        for member in self.members:
            checked_def = ENGINE.get_checked(member)
            match checked_def:
                case CheckedFunctionDef():
                    stub_asts_by_module.setdefault(checked_def.module, []).append(
                        checked_def.stub()
                    )
                case CheckedFunctionDecl():
                    stub_asts_by_module.setdefault(checked_def.module, []).append(
                        checked_def.stub()
                    )
                case _:
                    continue

        module_stubs: dict[str, str] = {}
        for module_name, stub_asts in stub_asts_by_module.items():
            module = importlib.import_module(module_name)
            import_map = DEF_STORE.sources.imports[module.__file__]

            module_ast = ast.Module(
                [
                    *(
                        [ast.Expr(ast.Constant(module.__doc__))]
                        if module.__doc__
                        else []
                    ),
                    *import_map.dump_ast(),
                    *stub_asts,
                ],
                type_ignores=[],
            )
            module_stubs[module_name] = ast.unparse(module_ast)

        return module_stubs


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
