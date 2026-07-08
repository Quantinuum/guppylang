"""Optimization configuration for Guppy compilation."""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Generic,
    ParamSpec,
    TypeVar,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from hugr.package import Package
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
                        remove_tuple_untuple=True,
                        remove_dead_funcs=True,
                        remove_redundant_order_edges=True,
                        squash_borrows=True,
                        inline_funcs=True,
                        # Tket reports invalid constructed HUGRs
                        # / "cannot modify indirect call" errors.
                        resolve_modifiers=True,
                        # Causes errors in the notebook examples;
                        # Emulation succeeds but shots lose expected result entries
                        # (`eigenvalue` / `attempts`), producing `KeyError` in the
                        # plotting cells.
                        simplify_cfgs=True,
                        # fails `test_arithmetic.py::test_float_to_int`
                        # Selene reports package validation error:
                        # `Node(...) has an unconnected port Port(Outgoing, 0)`
                        constant_folding=True,
                        # when combined with `inline_funcs=True` fails
                        # `test_qsystem_sol_functional`: tket/portgraph panic
                        # with `Outgoing port count exceeds maximum`
                        inline_dfgs=True,
                    )
                ]
            case OptimizationLevel.Minimal:
                return []


def _apply_passes(package: Package, passes: Sequence[ComposablePass]) -> Package:
    if not passes:
        return package

    # Compose the passes to trigger any cross-pass optimizations that may be possible.
    composed = functools.reduce(lambda x, y: x.then(y), passes)

    for module in package.modules:
        composed.run(module, inplace=True)

    return package


@dataclass(frozen=True)
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
            self.compile_function(), n_qubits, builder, libs, platform
        )

    def compile(self) -> Package:
        """Compile an execution entrypoint with the configured optimizations.

        Alias for :py:meth:`compile_entrypoint`.
        """
        return self.compile_entrypoint()

    def compile_entrypoint(self) -> Package:
        """Compile an entrypoint with the configured optimizations."""
        return _apply_passes(self.definition._compile_entrypoint(), self.passes)

    def compile_function(self) -> Package:
        """Compile a function with the configured optimizations."""
        return _apply_passes(self.definition._compile_function(), self.passes)
