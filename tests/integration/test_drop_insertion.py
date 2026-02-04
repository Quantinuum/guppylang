from guppylang.decorator import guppy
from guppylang.std.array import array
from guppylang_internals.decorator import custom_type
from guppylang_internals.std._internal.compiler.tket_exts import GUPPY_EXTENSION
from guppylang.std.lang import owned

from hugr import tys, ops
from hugr.package import Package
from hugr.std.collections.array import Array


@custom_type(Array(tys.Unit, 1), copyable=False, droppable=True)
class AffineTy:
    """A dummy affine type that lowers to a linear Hugr array.

    Implicit Guppy drops of values of this types need an explicit drop in Hugr.
    """


@guppy.declare
def make() -> AffineTy:
    """Creates an instance of `AffineTy`."""


def num_drops(pkg: Package) -> int:
    drop_op = GUPPY_EXTENSION.get_op("drop")
    h = pkg.modules[0]
    n = 0
    for node in h:
        match h[node].op:
            case ops.ExtOp() as ext_op:
                if ext_op.op_def().qualified_name() == drop_op.qualified_name():
                    n += 1
    return n


def test_drop(validate):
    @guppy
    def main(x: AffineTy @ owned) -> None:
        pass

    hugr = main.compile_function()
    assert num_drops(hugr) == 1
    validate(hugr)


def test_drop_nested(validate):
    @guppy.struct
    class MyStruct:
        x: AffineTy
        y: AffineTy
        z: float

    @guppy
    def main(
        xs: tuple[AffineTy, int] @ owned,
        y: MyStruct @ owned,  # Unpacked into individual wires
        z: array[MyStruct, 42] @ owned,
    ) -> None:
        pass

    hugr = main.compile_function()
    assert num_drops(hugr) == 4
    validate(hugr)


def test_drop_inout(validate):
    @guppy.declare
    def foo(x: AffineTy) -> None: ...

    @guppy
    def main() -> None:
        foo(make())  # Drops inout return

    hugr = main.compile_function()
    assert num_drops(hugr) == 1
    validate(hugr)


def test_drop_comprehension(validate):
    @guppy.declare
    def foo(x: AffineTy) -> AffineTy: ...

    @guppy
    def main(x: AffineTy @ owned) -> None:
        array(foo(x) for _ in range(10))
        # Drops x and the resulting array

    hugr = main.compile_function()
    assert num_drops(hugr) == 2
    validate(hugr)


def test_drop_reassign(validate):
    @guppy
    def main() -> AffineTy:
        x = make()
        x = make()  # Drops previous x
        return x

    hugr = main.compile_function()
    assert num_drops(hugr) == 1
    validate(hugr)


def test_drop_if(validate):
    @guppy
    def main(b: bool) -> AffineTy:
        x = make()
        if b:
            x = make()  # Drops previous x
        return x

    hugr = main.compile_function()
    assert num_drops(hugr) == 1
    validate(hugr)


def test_drop_while(validate):
    @guppy.declare
    def foo(x: AffineTy) -> bool: ...

    @guppy
    def main() -> AffineTy:
        x = make()
        y = make()
        while foo(x):  # Drops x when condition is false
            if foo(y):
                y = x  # Drops y
                break
            y = make()
            if not foo(x):
                return x  # Drops y
            x = make()  # Drops x
        return y

    hugr = main.compile_function()
    assert num_drops(hugr) == 4
    validate(hugr)
