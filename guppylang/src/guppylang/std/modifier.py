from hugr.package import Package
from tket.passes import ModifierResolverPass, NormalizeGuppy
from hugr.hugr import Hugr
from guppylang.defs import GuppyFunctionDefinition
from guppylang.emulator import EmulatorBuilder, EmulatorInstance


def build_emu(
    guppy_func: GuppyFunctionDefinition, n_qubits: int, norm: bool = True
) -> EmulatorInstance:
    package = guppy_func.compile()
    hugr = package.modules[0]
    extensions = package.extensions

    if norm:
        hugr = NormalizeGuppy()(hugr)

    hugr = apply_passes(hugr)

    if norm:
        hugr = NormalizeGuppy()(hugr)

    package = hugr.to_package()

    builder = EmulatorBuilder()

    return builder.build(package, n_qubits=n_qubits)


def apply_passes(hugr: Hugr) -> Hugr:
    modifier_passes = ModifierResolverPass()
    hugr = modifier_passes(hugr)

    return hugr
