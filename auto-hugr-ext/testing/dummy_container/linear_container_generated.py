from typing import Self


from guppylang import guppy
from guppylang.std.lang import Copy, owned

from pathlib import Path as _Path

from auto_hugr_ext import (
    auto_hugr_op,
    auto_hugr_type,
    load_extension,
    type_params_from_source,
)
from guppylang_internals.decorator import custom_type, hugr_op

_AUTO_HUGR_EXTENSION = load_extension(
    _Path(__file__).with_name('linear_container.json')
)



@custom_type(auto_hugr_type(_AUTO_HUGR_EXTENSION, 'LinearContainer'), name='LinearContainer', copyable=False, droppable=False, params=type_params_from_source("@ext_type(copyable=False, droppable=False)\nclass LinearContainer[T: Copy]:\n\n    @ext_op\n    def consume(self: 'Self' @ owned) -> T:\n        ..."))
class LinearContainer[T: Copy]:
    @hugr_op(auto_hugr_op(_AUTO_HUGR_EXTENSION, 'consume'), name='consume')
    def consume(self: "Self" @ owned) -> T: ...


@hugr_op(auto_hugr_op(_AUTO_HUGR_EXTENSION, 'make_container'), name='make_container')
def make_container[T: Copy](value: T) -> "LinearContainer[T]": ...


@hugr_op(auto_hugr_op(_AUTO_HUGR_EXTENSION, 'make_dummy_action'), name='make_dummy_action')
def dummy_action(a: bool, b: int) -> None: ...


@guppy
def main() -> None:
    value = make_container(42).consume()
    dummy_action(value == 42, value)


if __name__ == "__main__":
    main.compile()
