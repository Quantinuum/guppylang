"""Shared mutable cells with explicitly managed linear handles.

Borrowed operations thread their handle to preserve sequencing. Operations through
separate copies have no relative ordering without another dependency.
Compilation and execution require HUGR ptr 0.2 and a backend implementing that
extension. The QIS compiler pinned in this branch lacks that code generation.
A compatible compiler release is required before this API can be released.
"""

from typing import no_type_check

from guppylang_internals.decorator import custom_function, custom_type
from guppylang_internals.std._internal.compiler.ptr import PtrCompiler, ptr_to_hugr
from guppylang_internals.tys import Effect
from guppylang_internals.tys.param import TypeParam

from guppylang import guppy
from guppylang.std.lang import Copy, Drop, Function, owned
from guppylang.std.option import Option

_params = [TypeParam(0, "T", must_be_copyable=False, must_be_droppable=False)]


@custom_type(ptr_to_hugr, copyable=False, droppable=False, params=_params)
class Cell[T]:
    """A linear handle to a shared cell containing a value of type `T`.

    Each handle must be released with `free`. Copying a handle shares the cell;
    it never copies its payload, which may itself be linear.
    """

    @custom_function(PtrCompiler("New"), effects=[Effect.ANY])
    @no_type_check
    def __new__[T](value: T @ owned) -> "Cell[T]":
        """Move a value into a new cell."""

    @custom_function(PtrCompiler("Read"), effects=[Effect.ANY])
    @no_type_check
    def read[C: (Copy, Drop)](self: "Cell[C]") -> C:
        """Copy the stored value. The payload must support both copying and dropping."""

    @custom_function(PtrCompiler("Write"), effects=[Effect.ANY])
    @no_type_check
    def write[C: (Copy, Drop)](self: "Cell[C]", value: C) -> None:
        """Replace the stored value, discarding the previous one.

        The payload must support both copying and dropping.
        """

    @custom_function(PtrCompiler("Swap"), effects=[Effect.ANY])
    @no_type_check
    def swap[T](self: "Cell[T]", value: T @ owned) -> T:
        """Replace the payload and return its previous value, preserving ownership."""

    @custom_function(PtrCompiler("Dup"), effects=[Effect.ANY])
    @no_type_check
    def copy[T](self: "Cell[T]") -> "Cell[T]":
        """Create another handle to the same cell without copying the payload."""

    @custom_function(PtrCompiler("Eq"), effects=[Effect.ANY])
    @no_type_check
    def __eq__[T](self: "Cell[T]", other: "Cell[T]") -> bool:
        """Compare cell identity, retaining both borrowed handles.

        The handles must store the same type, which may be linear. Separate
        cells compare unequal even when their payloads have equal values.
        Use `copy` to obtain a second handle to the same cell. Guppy rejects
        borrowing the same handle variable twice in one comparison.
        """

    @guppy
    @no_type_check
    def __ne__[T](self: "Cell[T]", other: "Cell[T]") -> bool:
        """Return whether the handles refer to different cells."""
        return not self == other

    @custom_function(PtrCompiler("Free"), effects=[Effect.ANY])
    @no_type_check
    def free[T](self: "Cell[T]" @ owned) -> Option[T]:
        """Release this handle, returning the payload only for the last handle.

        Earlier releases return `nothing`. A linear payload in the returned
        option must still be consumed.
        """

    @custom_function(PtrCompiler("Map"), effects=[Effect.ANY])
    @no_type_check
    def map[T, In, Out](
        self: "Cell[T]",
        f: Function[[T @ owned, In @ owned], tuple[T, Out]],
        arg: In @ owned,
    ) -> Out:
        """Transform the payload with `f`, returning an additional result.

        The callback receives the payload and `arg`, and returns the replacement
        payload and a result. Both may be linear. Use tuples to carry multiple
        arguments or results, and `None` for no additional value.

        The runtime holds the cell lock throughout the callback. Accessing this
        cell through an alias inside the callback can deadlock even in a
        single-threaded program. For example, do not pass a copy of this handle
        as `arg` and call `read` on that copy from `f`. Access to a different
        cell is allowed. The compiler does not check aliases here, and no
        runtime panic on re-entry is currently guaranteed.
        """
