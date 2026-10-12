"""Tests for the optimization level configuration in `.compile` and `.emulator`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pytest
from guppylang import (
    GuppyCompilableProgram,
    OptimizationLevel,
    OptimizerInstance,
    guppy,
)
from guppylang.emulator.exceptions import EmulatorBuildError
from guppylang.optimizer import _RemoveRedundanciesPass
from hugr.metadata import HugrDebugInfo
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


def test_remove_redundancies_pass_definition() -> None:
    """Keep the pytket-free pass definition in sync with pytket's serialization."""
    pytket_passes = pytest.importorskip("pytket.passes")

    assert (
        _RemoveRedundanciesPass().to_dict()
        == pytket_passes.RemoveRedundancies().to_dict()
    )


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
    # compile successfully.
    assert len(package_minimal.modules[0]) > 0
    assert len(package_classical.modules[0]) > 0
    assert len(package_default.modules[0]) > 0


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


def test_target_platform_preserved_when_chaining_optimizations() -> None:
    """Test that target platform and optimization passes compose in either order."""

    first_pass = CountingPass()
    second_pass = CountingPass()

    @guppy
    def main() -> None:
        _x = 2 + 2

    platform_then_pass = main.with_target_platform("sol").with_optimization(first_pass)
    pass_then_platform = (
        main.with_minimal_opt()
        .with_optimization(second_pass)
        .with_target_platform("sol")
    )

    assert platform_then_pass.target_platform == "sol"
    assert platform_then_pass.passes[-1] is first_pass
    assert len(platform_then_pass.passes) == len(OptimizationLevel.Default.passes()) + 1
    assert pass_then_platform.target_platform == "sol"
    assert pass_then_platform.passes == [second_pass]

    platform_then_pass.compile()
    pass_then_platform.compile()
    assert first_pass.calls == 1
    assert second_pass.calls == 1


def test_reconfiguring_optimizer() -> None:
    """Test that selecting a new optimization level only replaces the passes."""

    custom_pass = CountingPass()

    @guppy
    def main() -> None:
        _x = 2 + 2

    default = main.with_target_platform("sol")
    configured = default.with_optimization(custom_pass)
    classical = configured.with_opt_level(OptimizationLevel.Classical)
    minimal = configured.with_minimal_opt()

    assert default.passes == OptimizationLevel.Default.passes()
    assert configured.passes[-1] is custom_pass
    assert classical.target_platform == "sol"
    assert classical.passes == OptimizationLevel.Classical.passes()
    assert minimal.target_platform == "sol"
    assert minimal.passes == OptimizationLevel.Minimal.passes()

    classical.compile()
    minimal.compile()
    assert custom_pass.calls == 0


def test_debug_emulator_requires_minimal_optimization() -> None:
    @guppy
    def main() -> None:
        pass

    with pytest.raises(EmulatorBuildError, match="with_minimal_opt"):
        main.emulator(n_qubits=0, debug_mode=True)

    with pytest.raises(EmulatorBuildError, match="with_minimal_opt"):
        main.with_opt_level(OptimizationLevel.Classical).emulator(
            n_qubits=0, debug_mode=True
        )

    with pytest.raises(EmulatorBuildError, match="with_minimal_opt"):
        main.with_minimal_opt().with_optimization(CountingPass()).emulator(
            n_qubits=0, debug_mode=True
        )


def test_debug_compile_allows_optimization() -> None:
    @guppy
    def main() -> None:
        pass

    hugr = (
        main.with_opt_level(OptimizationLevel.Classical)
        .compile(debug_mode=True)
        .modules[0]
    )
    meta = hugr[hugr.module_root].metadata
    assert HugrDebugInfo in meta
