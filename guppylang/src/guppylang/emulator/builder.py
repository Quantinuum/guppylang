"""
Compiling and building emulator instances for guppy programs.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

import selene_sim
from typing_extensions import Self

from .instance import EmulatorInstance

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from hugr.package import Package
    from selene_core import BuildPlanner, QuantumInterface, Utility


@dataclass(frozen=True)
class EmulatorBuilder:
    """A builder class for creating EmulatorInstance objects.

    Supports configuration parameters for compilation of emulator instances.
    """

    # interface supported parameters
    _name: str | None = None
    _build_dir: Path | None = None
    _verbose: bool = False

    # selene_sim supported parameters, may be added in the future:
    _planner: BuildPlanner | None = None
    _utilities: Sequence[Utility] | None = None
    _interface: QuantumInterface | None = None
    _progress_bar: bool = False
    _strict: bool = False
    _save_planner: bool = False
    _custom_args: dict[str, Any] | None = None

    @property
    def name(self) -> str | None:
        """User specified name for the emulator instance. Defaults to None."""
        return self._name

    @property
    def build_dir(self) -> Path | None:
        """Directory to store intermediate build files and execution results.
        Defaults to None, in which case a temporary directory is used."""
        return self._build_dir

    @property
    def verbose(self) -> bool:
        """Whether to print verbose output during the build process."""
        return self._verbose

    @property
    def custom_args(self) -> dict[str, Any] | None:
        """Custom build arguments passed to selene_sim.build."""
        return dict(self._custom_args) if self._custom_args is not None else None

    def with_name(self, value: str | None) -> Self:
        """Set the name for the emulator instance."""
        return replace(self, _name=value)

    def with_build_dir(self, value: Path | None) -> Self:
        """Set the build directory for the emulator instance,
        see `EmulatorBuilder.build_dir`."""
        return replace(self, _build_dir=value)

    def with_verbose(self, value: bool) -> Self:
        """Set whether to print verbose output during the build process."""
        return replace(self, _verbose=value)

    def with_build_arg(self, key: str, value: Any) -> Self:
        """Selene builds may support additional customisable arguments,
        e.g. to override the choice of compilation route. This is passed
        to selene_sim.build as kwargs.

        For example:

        .. code-block:: python

            .with_build_arg("build_method", "via-llvm_ir")

        is equivalent to

        .. code-block:: python

            selene_sim.build(..., build_method="via-llvm_ir")

        which saves LLVM IR into the build directory rather than
        saving bitcode.
        """
        if self._custom_args is None:
            return replace(self, _custom_args={key: value})
        else:
            return replace(self, _custom_args=self._custom_args | {key: value})

    def build(self, package: Package, n_qubits: int) -> EmulatorInstance:
        """Build an EmulatorInstance from a compiled package.

        Args:
            package: The compiled HUGR package to build the emulator from.
            n_qubits: The number of qubits to allocate for the emulator instance.

        Returns:
            An EmulatorInstance that can be used to run the compiled program.
        """

        instance = selene_sim.build(  # type: ignore[attr-defined]
            package,
            name=self._name,
            build_dir=self._build_dir,
            interface=self._interface,
            utilities=self._utilities,
            verbose=self._verbose,
            planner=self._planner,
            progress_bar=self._progress_bar,
            strict=self._strict,
            save_planner=self._save_planner,
            **self._custom_args or {},
        )

        return EmulatorInstance(_instance=instance, _n_qubits=n_qubits)
