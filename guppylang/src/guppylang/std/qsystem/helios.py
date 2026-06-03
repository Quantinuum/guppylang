"""Guppy library for Quantinuum Helios-specific operations."""

from typing import Any

from hugr.hugr.base import Hugr
from hugr.package import Package

# TODO: where should this definition live?
HELIOS_CONFIG_META_KEY = "qsystem.helios.configuration"


def set_platform_config(
    hugr: Package | Hugr[Any],
    squash_rxys: bool = True,
    enable_replay: bool = False,
    dd_threshold: int | None = None,
) -> None:
    """Set Helios-specific job configuration options on a compiled HUGR.

    Note that this configuration is *Helios-only* - it only has effect on cloud
    submissions to the Helios hardware and Helios-specific emulators. In particular, it
    has no effect for local simulator runs.

    Args:
        hugr: A compiled HUGR package or module to configure.
        squash_rxys: Whether to squash single-qubit gates at runtime (independent of any
            compile-time squashing). Defaults to True.
        enable_replay: Whether to enable replay logging. Defaults to False.
        dd_threshold: Dynamical decoupling threshold. Set to zero to enable DD with auto
            threshold, or to a nonzero value to manually specify a threshold. Set to
            None to disable DD (the default).
    """
    config = {
        "squash_rxys": squash_rxys,
        "enable_replay": enable_replay,
        "dd_threshold": dd_threshold,
    }
    modules = hugr.modules if isinstance(hugr, Package) else [hugr]
    for module in modules:
        module.module_root.metadata[HELIOS_CONFIG_META_KEY] = config
