"""Optimization configuration for Guppy compilation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Generic,
    ParamSpec,
    TypeVar,
)

from hugr.package import Package

if TYPE_CHECKING:
    from collections.abc import Sequence

    from hugr.passes.composable import ComposablePass

    from guppylang.defs import GuppyFunctionDefinition
    from guppylang.emulator import EmulatorBuilder, EmulatorInstance, Platform

__all__ = (
    "OptimizationLevel",
    "OptimizerInstance",
)

P = ParamSpec("P")
Out = TypeVar("Out")


class OptimizationLevel(Enum):
    """Optimization level used when compiling a Guppy program."""

    Default = "default"
    """
    Optimization set used by default for all Guppy program compilations.
    """

    Classical = "classical"
    """
    Only apply classical optimizations.

    Some gate rebasing/dead quantum code elimination may be applied as needed.
    """

    Minimal = "minimal"
    """
    Only apply structural rewrites required for execution.
    """

    def passes(self) -> list[ComposablePass]:
        """Return the HUGR passes that implement this optimization level."""
        match self:
            case OptimizationLevel.Default | OptimizationLevel.Classical:
                from tket import passes

                # TODO: Partially disabled due to tket2 issues. Re-enable these
                # flags as the corresponding tket bugs are fixed.
                return [
                    passes.NormalizeGuppy(
                        resolve_modifiers=False,
                        simplify_cfgs=False,
                        remove_tuple_untuple=True,
                        constant_folding=False,
                        # Removes public function declarations.
                        #
                        # See <https://github.com/Quantinuum/tket2/issues/1755>
                        remove_dead_funcs=False,
                        inline_dfgs=True,
                        remove_redundant_order_edges=False,
                        squash_borrows=True,
                    )
                ]
            case OptimizationLevel.Minimal:
                return []


def _sync_handles_metadata(package: Package) -> None:
    """Keep the node handle metadata in sync with main node data.

    Temporary workaround for <https://github.com/Quantinuum/tket2/issues/1757>.
    """
    for module in package.modules:
        root_metadata = module.module_root.metadata.as_dict()
        root_metadata.clear()
        root_metadata.update(module[module.module_root].metadata.as_dict())

        entrypoint_metadata = module.entrypoint.metadata.as_dict()
        entrypoint_metadata.clear()
        entrypoint_metadata.update(module[module.entrypoint].metadata.as_dict())


def _apply_passes(package: Package, passes: Sequence[ComposablePass]) -> Package:
    if not passes:
        return package

    modules = package.modules
    for pass_ in passes:
        next_package = Package(
            [pass_.run(module, inplace=False).hugr for module in modules],
            extensions=package.extensions,
        )
        # TODO: Temporary workaround for tket/hugr roundtrips leaving
        # module.module_root.metadata and module.entrypoint.metadata
        # disconnected from module[module.module_root].metadata.
        #
        # See <https://github.com/Quantinuum/tket2/issues/1757>
        #
        # We should be able to replace the whole loop contents with inline pass
        # runs once the above gets fixed.
        _sync_handles_metadata(next_package)

        package = next_package
        modules = package.modules
    return package


@dataclass
class OptimizerInstance(Generic[P, Out]):
    """Builder used to configure optimizations for compiling a Guppy program."""

    definition: GuppyFunctionDefinition[P, Out]
    passes: list[ComposablePass] = field(default_factory=list)

    def with_optimization(
        self, optimization: ComposablePass
    ) -> OptimizerInstance[P, Out]:
        """Add an additional optimization pass to run while compiling the program."""
        return OptimizerInstance(self.definition, [*self.passes, optimization])

    def emulator(
        self,
        n_qubits: int | None = None,
        builder: EmulatorBuilder | None = None,
        libs: list[Package] | None = None,
        platform: Platform = "helios",
    ) -> EmulatorInstance:
        """Compile this function for emulation with the configured optimizations."""
        return self.definition._emulator(
            self.compile(), n_qubits, builder, libs, platform
        )

    def compile(self) -> Package:
        """Compile an execution entrypoint with the configured optimizations."""
        return self.compile_entrypoint()

    def compile_entrypoint(self) -> Package:
        """Compile an entrypoint with the configured optimizations."""
        return _apply_passes(self.definition._compile_entrypoint(), self.passes)

    def compile_function(self) -> Package:
        """Compile a function with the configured optimizations."""
        return _apply_passes(self.definition._compile_function(), self.passes)
