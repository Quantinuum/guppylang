from dataclasses import dataclass

from hugr import ext, val
from tket_exts import (
    debug,
    futures,
    global_phase,
    guppy,
    measurement,
    modifier,
    qsystem_helios,
    qsystem_random,
    qsystem_sol,
    qsystem_utils,
    quantum,
    result,
    rotation,
    wasm,
)

DEBUG_EXTENSION = debug()
FUTURES_EXTENSION = futures()
GLOBAL_PHASE_EXTENSION = global_phase()
GUPPY_EXTENSION = guppy()
MEASUREMENT_EXTENSION = measurement()
MODIFIER_EXTENSION = modifier()
QSYSTEM_HELIOS_EXTENSION = qsystem_helios()
QSYSTEM_SOL_EXTENSION = qsystem_sol()
QSYSTEM_RANDOM_EXTENSION = qsystem_random()
QSYSTEM_UTILS_EXTENSION = qsystem_utils()
QUANTUM_EXTENSION = quantum()
RESULT_EXTENSION = result()
ROTATION_EXTENSION = rotation()
WASM_EXTENSION = wasm()

TKET_EXTENSIONS = [
    DEBUG_EXTENSION,
    FUTURES_EXTENSION,
    GLOBAL_PHASE_EXTENSION,
    GUPPY_EXTENSION,
    MEASUREMENT_EXTENSION,
    MODIFIER_EXTENSION,
    QSYSTEM_HELIOS_EXTENSION,
    QSYSTEM_SOL_EXTENSION,
    QSYSTEM_RANDOM_EXTENSION,
    QSYSTEM_UTILS_EXTENSION,
    QUANTUM_EXTENSION,
    RESULT_EXTENSION,
    ROTATION_EXTENSION,
    WASM_EXTENSION,
]


@dataclass(frozen=True)
class ConstWasmModule(val.ExtensionValue):
    """Python wrapper for the tket ConstWasmModule type"""

    wasm_file: str

    def to_value(self) -> val.Extension:
        ty = WASM_EXTENSION.get_type("module").instantiate([])

        name = "ConstWasmModule"
        payload = {"module_filename": self.wasm_file}
        return val.Extension(name, typ=ty, val=payload)

    def __str__(self) -> str:
        return f"tket.wasm.module(module_filename={self.wasm_file})"

    def _resolve_used_extensions_inplace(
        self,
        resolver: ext.UsedExtensionResolver,
        registry: ext.ExtensionRegistry | None = None,
    ) -> None:
        resolver.register(WASM_EXTENSION)
