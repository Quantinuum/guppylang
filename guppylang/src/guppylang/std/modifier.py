from hugr.package import Package
from tket.passes import ModifierResolverPass, NormalizeGuppy

from guppylang.defs import GuppyFunctionDefinition
from guppylang.emulator import EmulatorBuilder, EmulatorInstance


def build_emu(guppy_func: GuppyFunctionDefinition, n_qubits: int) -> EmulatorInstance:
    package = guppy_func.compile()
    hugr = package.modules[0]
    extensions = package.extensions

    hugr = NormalizeGuppy()(hugr)

    modifier_passes = ModifierResolverPass()
    hugr = modifier_passes(hugr)

    package = Package([hugr])

    builder = EmulatorBuilder()

    return builder.build(package, n_qubits=n_qubits)
