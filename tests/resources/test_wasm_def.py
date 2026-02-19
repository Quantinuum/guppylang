"""Module that uses @wasm_module with a relative path.

The wasm file lives alongside this module, so a relative path should resolve
correctly regardless of the working directory of the process that imports this.
"""

from guppylang_internals.decorator import wasm, wasm_module


@wasm_module("test.wasm")
class RelativeWasm:
    @wasm
    def two(self: "RelativeWasm") -> int: ...

    @wasm
    def add(self: "RelativeWasm", x: int, y: int) -> int: ...
