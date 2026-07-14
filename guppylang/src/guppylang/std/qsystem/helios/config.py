"""Platform configuration interface for HUGRs targeting Helios."""

from typing import Any

from hugr.hugr.base import Hugr
from hugr.package import Package

# TODO: where should this definition live?
HELIOS_CONFIG_META_KEY = "qsystem.helios.configuration"


def set_platform_config(
    hugr: Package | Hugr[Any],
    squash_rxys: bool = True,
    enable_dd: bool = False,
) -> None:
    """EXPERIMENTAL: Set Helios-specific job configuration options on a compiled HUGR.
    This is currently provided for development purposes only - options may not work as
    expected (or at all) and the interface may change in future releases.

    Note that this configuration is *Helios-only* - it only has effect on cloud
    submissions to the Helios hardware and Helios-specific emulators. In particular, it
    has no effect for local simulator runs.

    Args:
        hugr: A compiled HUGR package or module to configure.
        squash_rxys: Whether to combine single-qubit gates at runtime
                        (independent of any compile-time squashing). Defaults to True.
        enable_dd: Enable dynamical decoupling. Defaults to False.
    """
    config = {
        "squash_rxys": squash_rxys,
        "enable_dd": enable_dd,
    }
    modules = hugr.modules if isinstance(hugr, Package) else [hugr]
    for module in modules:
        module[module.module_root].metadata[HELIOS_CONFIG_META_KEY] = config.copy()
