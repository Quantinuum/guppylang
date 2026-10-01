"""Shared mutable cells with explicitly managed linear handles.

Borrowed operations thread their handle to preserve sequencing. Operations through
separate copies have no relative ordering without another dependency.
Concurrent execution requires a runtime providing pointer synchronization.
The standard emulator cannot execute these operations until its code generator
and runtime implement the pointer extension.
"""

from typing import no_type_check

from guppylang_internals.decorator import custom_function, custom_type
from guppylang_internals.std._internal.compiler.ptr import PtrCompiler, ptr_to_hugr
from guppylang_internals.tys import Effect
from guppylang_internals.tys.param import TypeParam

from guppylang import guppy
from guppylang.std.lang import Function, owned
from guppylang.std.option import Option

T = guppy.type_var("T", copyable=False, droppable=False)
In = guppy.type_var("In", copyable=False, droppable=False)
Out = guppy.type_var("Out", copyable=False, droppable=False)
Copyable = guppy.type_var("Copyable")
_params = [TypeParam(0, "T", must_be_copyable=False, must_be_droppable=False)]


@custom_type(ptr_to_hugr, copyable=False, droppable=False, params=_params)
class Ptr[T]:
    """A linear handle to a shared cell containing a value of type `T`.

    Each handle must be released with `free`. Copying a handle shares the cell;
    it never copies its payload, which may itself be linear.
    """

    @custom_function(PtrCompiler("New"), effects=[Effect.ANY])
    @no_type_check
    def __new__(value: T @ owned) -> "Ptr[T]":
        """Move a value into a new cell."""

    @custom_function(PtrCompiler("Read"), effects=[Effect.ANY])
    @no_type_check
    def read(self: "Ptr[Copyable]") -> Copyable:
        """Copy the stored value. The payload must support both copying and dropping."""

    @custom_function(PtrCompiler("Write"), effects=[Effect.ANY])
    @no_type_check
    def write(self: "Ptr[Copyable]", value: Copyable) -> None:
        """Replace the stored value, discarding the previous one.

        The payload must support both copying and dropping.
        """

    @custom_function(PtrCompiler("Swap"), effects=[Effect.ANY])
    @no_type_check
    def swap(self: "Ptr[T]", value: T @ owned) -> T:
        """Replace the payload and return its previous value, preserving ownership."""

    @custom_function(PtrCompiler("Dup"), effects=[Effect.ANY])
    @no_type_check
    def copy(self: "Ptr[T]") -> "Ptr[T]":
        """Create another handle to the same cell without copying the payload."""

    @custom_function(PtrCompiler("Free"), effects=[Effect.ANY])
    @no_type_check
    def free(self: "Ptr[T]" @ owned) -> Option[T]:
        """Release this handle, returning the payload only for the last handle.

        Earlier releases return `nothing`. A linear payload in the returned
        option must still be consumed.
        """

    @custom_function(PtrCompiler("Map"), effects=[Effect.ANY])
    @no_type_check
    def map(
        self: "Ptr[T]",
        f: Function[[T @ owned, In @ owned], tuple[T, Out]],
        arg: In @ owned,
    ) -> Out:
        """Transform the payload with `f`, returning an additional result.

        The callback receives the payload and `arg`, and returns the replacement
        payload and a result. Both may be linear. Use tuples to carry multiple
        arguments or results, and `None` for no additional value.

        The runtime holds the cell lock throughout the callback. The callback
        must not access this same cell through another handle: re-entry may
        deadlock. This restriction is not checked by the compiler.
        """
