"""Optimization configuration for Guppy compilation.

Guppy applies a predefined set of optimization passes when compiling a program
using the TKET compiler.

These passes clean up artifacts introduced by the compiler and may simplify both
classical and quantum operations when calling ``compile()``,
``compile_function()``, or ``emulator()``.

Use ``with_opt_level()`` before compiling or creating an emulator to select a
different :py:class:`OptimizationLevel`. The method can be chained before
compiling or creating an emulator.


Choosing an optimization level
------------------------------

Pass a member of :py:class:`OptimizationLevel` to ``with_opt_level()``:

.. code-block:: python

    from guppylang import OptimizationLevel, guppy
    from guppylang.std.builtins import output
    from guppylang.std.quantum import h, measure, qubit

    @guppy
    def main() -> None:
        q = qubit()
        h(q)
        h(q)
        if measure(q):
            output("result", 2 + 2)
        else:
            output("result", 3 + 3)

    # Classical optimization will keep the self-inverse Hadamard gates.
    package = main.with_opt_level(OptimizationLevel.Classical).compile()

The available levels are:

* :py:attr:`OptimizationLevel.Default` applies Guppy's standard optimization
  level. This may include both classical and quantum optimizations that do
  not alter the program's gateset. Calling ``main.compile()`` or
  ``main.emulator(...)`` directly uses this level.
* :py:attr:`OptimizationLevel.Classical` restricts optimization to classical
  operations. The program will execute the same quantum operations as the original
  source, but may have a simplified control flow structure.
* :py:attr:`OptimizationLevel.Minimal` applies only structural rewrites needed
  to produce executable output. This is useful for low-level program analysis or
  when more control over the optimization passes is desired.

See :py:class:`OptimizationLevel` for more details.

Note that gate rebasing or other program transformations may still be performed
further down the compilation pipeline where required. For example, emulators may
require a specific gateset when targeting a particular architecture.

``with_minimal_opt()`` is shorthand for selecting :py:attr:`OptimizationLevel.Minimal`.
It disables optional optimizations on the program.

.. code-block:: python

    emulator = main.with_minimal_opt().emulator(n_qubits=1)


Running custom passes
---------------------

Use :py:meth:`OptimizerInstance.with_optimization` to append any HUGR
``ComposablePass`` to an optimization pipeline. For example, the following
starts with minimal optimization and then runs tket's function-inlining pass:

.. code-block:: python

    from tket.passes import InlineFunctions

    # Apply a tket pass to inline Guppy functions
    package = main.with_minimal_opt().with_optimization(InlineFunctions()).compile()

    package = (
        main.with_minimal_opt().with_optimization(passes.InlineFunctions())
        .compile()
    )

Multiple custom passes can be added by chaining ``with_optimization()`` calls.
They run in the order they are added, after the passes supplied by the selected
optimization level:

.. code-block:: python

    package = (
        main.with_opt_level(OptimizationLevel.Classical)
        .with_optimization(first_pass)
        .with_optimization(second_pass)
        .compile()
    )


Setting the target platform
-----------------------------

Use ``with_target_platform()`` to select the quantum platform targeted when
compiling for emulation. The setting composes with optimization configuration,
so the methods may be chained in either order:

.. code-block:: python

    emulator = (
        main.with_opt_level(OptimizationLevel.Classical)
        .with_target_platform("sol")
        .emulator(n_qubits=1)
    )

Passing ``platform`` directly to ``emulator()`` overrides the configured target.
If neither is specified, the emulator targets ``"helios"``.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import (
    TYPE_CHECKING,
    ParamSpec,
    TypeVar,
)

from tket import passes

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
    Guppy's standard optimization level.

    This may include both classical and quantum optimizations that do not alter
    the program's gateset. Calling ``main.compile()`` or ``main.emulator(...)``
    directly uses this level.

    Currently, this applies pytket's `RemoveRedundancies` after the
    optimizations in :py:attr:`OptimizationLevel.Classical`. This may be
    modified in future versions.
    """

    Classical = "classical"
    """
    Restricts optimization to classical operations.

    The program will execute the same quantum operations as the original source,
    but may have a simplified control flow structure.

    Currently, this runs tket's `Normalize
    <https://quantinuum.github.io/tket2/generated/tket.passes.Normalize.html#tket.passes.Normalize>`_
    pass to simplify classical control flow and remove redundant classical
    operations. This set may be modified in future versions.
    """

    Minimal = "minimal"
    """
    Applies only structural rewrites needed to produce executable output.

    This is useful for low-level program analysis or when more control over
    the optimization passes is desired.
    """

    def passes(self) -> list[ComposablePass]:
        """Return the list of HUGR passes ran by this optimization level."""
        match self:
            case OptimizationLevel.Default:
                return [
                    passes.Normalize(),
                    passes.PytketHugrPass(_RemoveRedundanciesPass()),
                ]
            case OptimizationLevel.Classical:
                return [passes.Normalize()]
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
class OptimizerInstance[**P, Out]:
    """Builder used to configure optimizations for compiling a Guppy program.

    Obtained by calling :py:meth:`GuppyFunctionDefinition.with_opt_level` or
    :py:meth:`GuppyFunctionDefinition.with_minimal_opt`.

    See :py:mod:`guppylang.optimizer` for usage examples.
    """

    definition: GuppyFunctionDefinition[P, Out]
    passes: list[ComposablePass] = field(default_factory=list)
    target_platform: Platform | None = field(default=None)

    def with_opt_level(self, level: OptimizationLevel) -> OptimizerInstance[P, Out]:
        """Configure the optimization level used when compiling this function.

        This overrides any previously configured optimization level or custom passes."""
        return replace(self, passes=level.passes())

    def with_minimal_opt(self) -> OptimizerInstance[P, Out]:
        """Configure the function to use minimal optimization when compiling.

        Equivalent to `with_opt_level(OptimizationLevel.Minimal)`, thus it overrides
        any previously configured optimization level or custom passes."""
        return self.with_opt_level(OptimizationLevel.Minimal)

    def with_optimization(
        self, optimization: ComposablePass
    ) -> OptimizerInstance[P, Out]:
        """Add an additional optimization pass to run while compiling the program."""
        return replace(self, passes=[*self.passes, optimization])

    def with_target_platform(self, platform: Platform) -> OptimizerInstance[P, Out]:
        """Set the default platform used by the emulator."""
        return replace(self, target_platform=platform)

    def emulator(
        self,
        n_qubits: int | None = None,
        builder: EmulatorBuilder | None = None,
        libs: list[Package] | None = None,
        platform: Platform | None = None,
        debug_mode: bool = False,
    ) -> EmulatorInstance:
        """Compile this function for emulation with the configured optimizations."""

        # If platform is set, use it.
        # Else if platform is not explicitly provided, use the target platform
        # Otherwise, no platform is set, thus use the default: "helios".
        platform = platform or self.target_platform
        if platform is None:
            platform = "helios"

        return self.definition._emulator(
            self.compile_function(debug_mode), n_qubits, builder, libs, platform
        )

    def compile(self, debug_mode: bool = False) -> Package:
        """Compile an execution entrypoint with the configured optimizations.

        Alias for :py:meth:`compile_entrypoint`.
        """
        return self.compile_entrypoint(debug_mode)

    def compile_entrypoint(self, debug_mode: bool = False) -> Package:
        """Compile an entrypoint with the configured optimizations."""
        return _apply_passes(
            self.definition._compile_entrypoint(debug_mode), self.passes
        )

    def compile_function(self, debug_mode: bool = False) -> Package:
        """Compile a function with the configured optimizations."""
        return _apply_passes(self.definition._compile_function(debug_mode), self.passes)


@dataclass(frozen=True, slots=True)
class _RemoveRedundanciesPass:
    """Clone of pytket's RemoveRedundancies pass definition that does not
    require pytket to be available."""

    def to_dict(self) -> dict[str, object]:
        return {
            "StandardPass": {"name": "RemoveRedundancies"},
            "pass_class": "StandardPass",
        }
