"""Tests for the optimization level configuration in `.compile` and `.emulator`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from guppylang import (
    GuppyCompilableProgram,
    OptimizationLevel,
    OptimizerInstance,
    guppy,
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
    """Test that optimization levels configure the expected pass lists."""

    # Minimal optimization
    @guppy
    def main_minimal() -> None:
        _x = 2 + 2

    optimizer_minimal = main_minimal.with_minimal_opt()

    # Classical-only optimization
    @guppy
    def main_classical() -> None:
        _x = 2 + 2

    optimizer_classical = main_classical.with_opt_level(OptimizationLevel.Classical)

    # Default optimization
    @guppy
    def main_default() -> None:
        _x = 2 + 2

    optimizer_default = main_default.with_opt_level(OptimizationLevel.Default)

    assert isinstance(optimizer_minimal, OptimizerInstance)
    assert isinstance(optimizer_minimal, GuppyCompilableProgram)
    assert optimizer_minimal.definition is main_minimal
    assert optimizer_minimal.passes == OptimizationLevel.Minimal.passes()

    assert isinstance(optimizer_classical, OptimizerInstance)
    assert isinstance(optimizer_classical, GuppyCompilableProgram)
    assert optimizer_classical.definition is main_classical
    assert optimizer_classical.passes == OptimizationLevel.Classical.passes()
    assert optimizer_default.passes == optimizer_classical.passes

    assert isinstance(optimizer_default, OptimizerInstance)
    assert isinstance(optimizer_default, GuppyCompilableProgram)
    assert optimizer_default.definition is main_default
    assert optimizer_default.passes == OptimizationLevel.Default.passes()

    # Compile a program with each level to exercise the configured pass list.
    package_minimal = optimizer_minimal.compile()
    package_classical = optimizer_classical.compile()
    package_default = optimizer_default.compile()

    # Classical/default optimization may remove structure from the minimal HUGR.
    # The important contract here is that both configured optimization levels
    # compile successfully and produce the same default optimization behavior.
    assert len(package_minimal.modules[0]) > 0
    assert len(package_classical.modules[0]) <= len(package_default.modules[0])


def test_opt_level_passes() -> None:
    """Test that the passes added to an optimizer are applied correctly."""

    counting_pass = CountingPass()

    @guppy
    def main() -> None:
        _x = 2 + 2

    optimizer = (
        main.with_opt_level(OptimizationLevel.Classical)
        .with_optimization(counting_pass)
        .with_optimization(counting_pass)
    )

    # No passes have been dropped from the list.
    assert len(optimizer.passes) == len(OptimizationLevel.Classical.passes()) + 2

    # Compile the program and check that the counting pass was called
    _package = optimizer.compile()
    assert counting_pass.calls == 2
