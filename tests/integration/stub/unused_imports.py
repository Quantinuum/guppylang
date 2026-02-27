"""Basic tests for generating Guppy stubs."""

from guppylang import guppy, comptime
from ast import Module  # noqa: F401, this should be removed in the stub
from guppylang.std.quantum import qubit, discard  # Should be removed in the stub
from guppylang.std.array import array, array_swap, frozenarray  # noqa: F401 One of the aliases gets removed.
from guppylang.std.angles import angle
from guppylang.std.num import nat


@guppy
def lib_func(x: int) -> int:
    return x


@guppy
def lib_func_using_import_in_body(x: int) -> int:
    discard(qubit())

    return x


@guppy
def lib_func_using_import_in_args_plain(x: angle) -> None:
    pass


@guppy
def lib_func_using_import_in_args_string(x: "nat") -> None:
    pass


@guppy
def lib_func_using_import_in_return_plain() -> array[int, 3]:
    return array(1, 2, 3)


@guppy
def lib_func_using_import_in_return_string() -> "frozenarray[int, 3]":
    return comptime(list(range(3)))
