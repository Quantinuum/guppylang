from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from guppylang.decorator import custom_guppy_decorator, guppy

if TYPE_CHECKING:
    from guppylang.defs import GuppyFunctionDefinition
    from hugr.package import Package, PackagePointer


@custom_guppy_decorator
def compile_guppy(fn) -> Package:
    """A decorator that combines @guppy with HUGR compilation."""
    defn: GuppyFunctionDefinition = guppy(fn)
    return defn.compile_function()


def dump_llvm(package: PackagePointer):
    try:
        from selene_hugr_qis_compiler import compile_to_llvm_ir

        llvm_module = compile_to_llvm_ir(package.package.to_bytes())
        print(llvm_module)  # noqa: T201

    except ImportError:
        pass


def get_wasm_file() -> str:
    return str(Path(__file__).parent.resolve() / "resources/test.wasm")


def get_h2_wasm_file() -> str:
    return str(Path(__file__).parent.resolve() / "resources/test.h2.wasm")


def compile_and_get_peak_memory(
    guppy_fn: GuppyFunctionDefinition, n_compilations: int = 1
) -> float:
    """Compile the given Guppy function `n_compilations` times and
    return the peak memory used in bytes as reported by
    `tracemalloc.get_traced_memory()`."""
    import gc
    import tracemalloc

    gc.disable()
    tracemalloc.start()
    for _ in range(n_compilations):
        guppy_fn.compile()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    gc.enable()
    _ = gc.collect()
    return peak
