"""Whether imports are correctly marked as used / unused by stubs."""
from guppylang import guppy
from guppylang.std.array import array, frozenarray
from guppylang.std.angles import angle
from guppylang.std.num import nat

@guppy.declare
def lib_func(x: int) -> int:
    ...

@guppy.declare
def lib_func_using_import_in_body(x: int) -> int:
    ...

@guppy.declare
def lib_func_using_import_in_args_plain(x: angle) -> None:
    ...

@guppy.declare
def lib_func_using_import_in_args_string(x: 'nat') -> None:
    ...

@guppy.declare
def lib_func_using_import_in_return_plain() -> array[int, 3]:
    ...

@guppy.declare
def lib_func_using_import_in_return_string() -> 'frozenarray[int, 3]':
    ...