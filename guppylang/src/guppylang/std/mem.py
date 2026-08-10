"""Utilities for advanced usage of ownership and borrowing."""

from typing import no_type_check

from guppylang_internals.decorator import custom_function
from guppylang_internals.std._internal.compiler.mem import WithOwnedCompiler
from guppylang_internals.std._internal.compiler.prelude import MemSwapCompiler
from guppylang_internals.tys import Effect

from guppylang import guppy
from guppylang.std.lang import Function, owned

T = guppy.type_var("T", copyable=False, droppable=False)
Out = guppy.type_var("Out", copyable=False, droppable=False)


@custom_function(MemSwapCompiler())
@no_type_check
def mem_swap(x: T, y: T) -> None:
    """Swaps the values of two variables."""


# For now we conservatively assume that any `Function` may have any effect.
# Otherwise we would somehow have to plumb through the effects of parameter `f`.
@custom_function(WithOwnedCompiler(), effects=[Effect.ANY])
@no_type_check
def with_owned(val: T, f: Function[[T @ owned], tuple[Out, T]]) -> Out:
    """Runs a closure where the borrowed argument is promoted to an owned one.

    The closure should return two values:

    * A generic return value that will be passed through.
    * Another value of type `T` that is written back into the borrowed place. This can
      either be the original passed value, or a new value of the same type that was
      created in the closure.

    Pretending that `val` is a pointer, this would be equivalent to the following
    operation in Rust/C: ``(out, *val) = f(*val)``
    """
