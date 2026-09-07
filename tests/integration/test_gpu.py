from guppylang_internals.decorator.gpu import gpu_module, gpu
from guppylang.decorator import guppy
from guppylang.std.builtins import nat


def test_gpu_functions(validate):
    @gpu_module("module", "config")
    class MyModule:
        @gpu
        def add_one(self: "MyModule", x: int) -> int: ...

        @gpu(42)
        def foo(self: "MyModule", x: int, y: float) -> int: ...

    @guppy
    def main() -> int:
        mod = MyModule()
        two = mod.add_one(1)
        two2 = mod.foo(two, 3.0)
        mod.discard()
        return two + two2

    mod = main.compile()
    validate(mod)


def test_gpu_methods(validate):
    @gpu_module("module", "config")
    class MyModule:
        @gpu
        def foo(self: "MyModule") -> int: ...

        @guppy
        def bar(self: "MyModule", x: int) -> int:
            return x + 1

    @guppy
    def main() -> int:
        mod = MyModule()
        x = mod.foo()
        _y = mod.bar(x)
        mod.discard()
        return x

    mod = main.compile()
    validate(mod)


def test_gpu_types(validate):
    @gpu_module("", None)
    class MyModule:
        @gpu
        def foo(self: "MyModule", x: int, y: float, z: nat) -> None: ...

    @guppy
    def main() -> None:
        mod = MyModule()
        mod.foo(-1, 2.0, 3)
        mod.discard()
        return

    mod = main.compile()
    validate(mod)


def test_lookup_by_id(validate):
    from hugr.ops import AsExtOp

    @gpu_module("", None)
    class MyGpu:
        @gpu(1)
        def foo(self: "MyGpu") -> int: ...

    @guppy
    def main() -> int:
        c = MyGpu()
        x = c.foo()
        c.discard()
        return x

    mod = main.compile()
    validate(mod)

    ops = set()
    for hugr in mod.modules[:]:
        for _, node in hugr.nodes():
            match node.op:
                case AsExtOp():
                    ops |= {node.op.op_def().name}
                case _:
                    pass
    assert "lookup_by_id" in ops
    assert "lookup_by_name" not in ops


def test_lookup_by_name(validate):
    from hugr.ops import AsExtOp

    @gpu_module("", None)
    class MyGpu:
        @gpu
        def foo(self: "MyGpu") -> int: ...

    @guppy
    def main() -> int:
        c = MyGpu()
        x = c.foo()
        c.discard()
        return x

    mod = main.compile()
    validate(mod)

    ops = set()
    for hugr in mod.modules[:]:
        for _, node in hugr.nodes():
            match node.op:
                case AsExtOp():
                    ops |= {node.op.op_def().name}
                case _:
                    pass
    assert "lookup_by_name" in ops
    assert "lookup_by_id" not in ops
