from typing import Self

from auto_hugr_ext import ext_op, ext_type
from guppylang.std.lang import Copy, owned


@ext_type(copyable=False, droppable=False)
class LinearContainer[T: Copy]:
    @ext_op
    def consume(self: "Self" @ owned) -> T: ...


@ext_op
def make_container[T: Copy](value: T) -> "LinearContainer[T]": ...


@ext_op(override_name="make_dummy_action")
def dummy_action(a: bool, b: int) -> None: ...