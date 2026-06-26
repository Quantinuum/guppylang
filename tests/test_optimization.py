"""Tests for the optimization level configuration in `.compile` and `.emulator`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from guppylang import guppy
from guppylang.optimizer import (
    GuppyCompilableProgram,
    OptimizationLevel,
    OptimizerInstance,
)
from hugr.passes.composable import ComposablePass, PassResult

if TYPE_CHECKING:
    from hugr.hugr import Hugr
    from hugr.passes.scope import PassScope


@dataclass
class CountingPass(ComposablePass):
    """A pass that counts how many times it was called."""

    calls: int = 0

    def run(self, hugr: Hugr[Any], *, inplace: bool = True) -> PassResult:
        self.calls += 1
        return PassResult.for_pass(
            self, hugr, result=None, inplace=inplace, modified=False
        )

    def with_scope(self, scope: PassScope) -> ComposablePass:
        return self


def test_opt_levels() -> None:
    """Test that changing the optimization levels affects the compiled HUGR."""

    # Minimal optimization
    @guppy
    def main_minimal() -> None:
        _x = 2 + 2

    optimizer_minimal = main_minimal.with_opt_level(OptimizationLevel.Minimal)

    # Default optimization
    @guppy
    def main_default() -> None:
        _x = 2 + 2

    optimizer_default = main_default.with_opt_level(OptimizationLevel.Default)

    assert isinstance(optimizer_minimal, OptimizerInstance)
    assert isinstance(optimizer_minimal, GuppyCompilableProgram)
    assert optimizer_minimal.definition is main_minimal
    assert optimizer_minimal.passes == OptimizationLevel.Minimal.passes()

    assert isinstance(optimizer_default, OptimizerInstance)
    assert isinstance(optimizer_default, GuppyCompilableProgram)
    assert optimizer_default.definition is main_default
    assert optimizer_default.passes == OptimizationLevel.Default.passes()

    # Compile the programs and compare their sizes
    package_minimal = optimizer_minimal.compile()
    package_default = optimizer_default.compile()

    assert len(package_minimal.modules[0]) > len(package_default.modules[0])


def test_opt_level_passes() -> None:
    """Test that the passes added to an optimizer are applied correctly."""

    counting_pass = CountingPass()

    @guppy
    def main() -> None:
        _x = 2 + 2

    optimizer = (
        main.with_opt_level(OptimizationLevel.Default)
        .with_optimization(counting_pass)
        .with_optimization(counting_pass)
    )

    # No passes have been dropped from the list.
    assert len(optimizer.passes) == len(OptimizationLevel.Default.passes()) + 2

    # Compile the program and check that the counting pass was called
    _package = optimizer.compile()
    assert counting_pass.calls == 2
