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
from tket import passes

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
            case OptimizationLevel.Default:
                return [passes.NormalizeGuppy()]
            case OptimizationLevel.Classical:
                return [passes.NormalizeGuppy()]
            case OptimizationLevel.Minimal:
                return []


def _apply_passes(package: Package, passes: Sequence[ComposablePass]) -> Package:
    if not passes:
        return package

    modules = package.modules
    for pass_ in passes:
        modules = [pass_.run(module, inplace=False).hugr for module in modules]
    return Package(modules=modules, extensions=package.extensions)


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
