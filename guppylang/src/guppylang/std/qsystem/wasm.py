"""Guppy standard library for WebAssembly-style (wasm) contexts"""

from collections.abc import Callable
from typing import no_type_check

from guppylang.decorator import guppy
from guppylang.std.builtins import array, comptime, nat

T = guppy.type_var("T", copyable=False, droppable=False)


@guppy
@no_type_check
def spawn_wasm_contexts(n: nat @ comptime, spawn: Callable[[nat], T]) -> "array[T, n]":  # noqa: F821
    return array(spawn(nat(ix)) for ix in range(n))
