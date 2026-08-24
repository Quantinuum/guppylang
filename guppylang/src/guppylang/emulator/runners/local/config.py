"""Configuration for running on local backends."""

from collections.abc import Callable
from typing import Any

import pydantic as pyd
from selene_core import Simulator

from guppylang.emulator.runners.base.backend_config import RunnerConfig


class LocalRunnerConfig(RunnerConfig):
    """Configuration for running on local backends."""

    backend: Simulator | None = pyd.Field(default=None)
    """Simulation backend to use. If None, a default backend will be chosen
    based on the mode. For most cases, default backends should be sufficient.
    """

    runtime_register_hook: Callable[[Any], None] | None
    """A hook to register additional runtime components. If None, no additional
    components will be registered. This can be used to register custom event hooks
    or other runtime components.
    """

    build_kwargs: dict[str, Any] = pyd.Field(default_factory=dict)
    """keyword arguments to pass to the Selene build function."""

    with_circuit_extraction: bool = pyd.Field(default=False)
    """Whether to perform circuit extraction during program execution.
    If True, a CircuitExtractor will be used as an event hook during execution to
    extract the executed circuit for each shot.
    """

    with_metric_store: bool = pyd.Field(default=False)
    """Whether to store metrics during program execution. If True, a MetricStore
    will be used as an event hook during execution to store metrics.
    """
