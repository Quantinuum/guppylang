from dataclasses import dataclass

import tket_exts
from hugr import val
from tket_exts import (
    debug,
    futures,
    global_phase,
    guppy,
    modifier,
    qsystem,
    qsystem_random,
    qsystem_utils,
    quantum,
    result,
    rotation,
    wasm,
)

BOOL_EXTENSION = tket_exts.bool()
DEBUG_EXTENSION = debug()
FUTURES_EXTENSION = futures()
GLOBAL_PHASE_EXTENSION = global_phase()
GUPPY_EXTENSION = guppy()
MODIFIER_EXTENSION = modifier()
QSYSTEM_EXTENSION = qsystem()
QSYSTEM_RANDOM_EXTENSION = qsystem_random()
QSYSTEM_UTILS_EXTENSION = qsystem_utils()
QUANTUM_EXTENSION = quantum()
RESULT_EXTENSION = result()
ROTATION_EXTENSION = rotation()
WASM_EXTENSION = wasm()

TKET_EXTENSIONS = [
    BOOL_EXTENSION,
    DEBUG_EXTENSION,
    FUTURES_EXTENSION,
    GLOBAL_PHASE_EXTENSION,
    GUPPY_EXTENSION,
    MODIFIER_EXTENSION,
    QSYSTEM_EXTENSION,
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
        return val.Extension(name, typ=ty, val=payload, extensions=["tket.wasm"])

    def __str__(self) -> str:
        return f"tket.wasm.module(module_filename={self.wasm_file})"
