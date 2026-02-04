from guppylang import guppy
from guppylang_internals.decorator import wasm, wasm_module
from guppylang.std.qsystem.wasm import spawn_wasm_contexts


def test_wasm_functions(validate, wasm_file):
    @wasm_module(wasm_file)
    class MyWasm:
        @wasm
        def two(self: "MyWasm") -> int: ...

        @wasm
        def add(self: "MyWasm", x: int, y: int) -> int: ...

        @wasm
        def fid(self: "MyWasm", x: float) -> float: ...

        @wasm
        def consume_float(self: "MyWasm", x: float) -> None: ...

        @wasm
        def nothing(self: "MyWasm") -> None: ...

    @guppy
    def main() -> int:
        [mod1, mod2] = spawn_wasm_contexts(2, MyWasm)
        two1 = mod1.two()
        two2 = mod2.two()
        four = mod2.add(two1, two2)
        f = mod1.fid(42.0)
        mod1.consume_float(f)
        mod1.discard()
        mod2.nothing()
        mod2.discard()
        return four + two2

    mod = main.compile_function()
    validate(mod)


def test_wasm_function_indices(validate, wasm_file):
    @wasm_module(wasm_file)
    class MyWasm:
        @wasm(1)
        def foo(self: "MyWasm") -> int: ...

        @wasm(0)
        def bar(self: "MyWasm", x: int, y: int) -> int: ...

        @wasm(3)
        def baz(self: "MyWasm", x: float) -> None: ...

        @wasm(4)
        def side_effect(self: "MyWasm") -> None: ...

    @guppy
    def main() -> int:
        [mod1, mod2] = spawn_wasm_contexts(2, MyWasm)
        two1 = mod1.foo()
        two2 = mod2.foo()
        four = mod2.bar(two1, two2)
        mod1.baz(42.0)
        mod2.side_effect()
        mod1.discard()
        mod2.discard()
        return four + two2

    mod = main.compile_function()
    validate(mod)


def test_wasm_methods(validate, wasm_file):
    @wasm_module(wasm_file)
    class MyWasm:
        @wasm
        def two(self: "MyWasm") -> int: ...

        @guppy
        def bar(self: "MyWasm", x: int) -> int:
            return x + 1

    @guppy
    def main() -> int:
        mod = MyWasm(1)
        x = mod.two()
        y = mod.bar(x)
        mod.discard()
        return x

    mod = main.compile_function()
    validate(mod)


def test_lookup_by_id(validate, wasm_file):
    from hugr.ops import AsExtOp

    @wasm_module(wasm_file)
    class MyWasm:
        @wasm(1)
        def foo(self: "MyWasm") -> int: ...

    @guppy
    def main() -> int:
        c = MyWasm(1)
        x = c.foo()
        c.discard()
        return x

    mod = main.compile_function()
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


def test_lookup_by_name(validate, wasm_file):
    from hugr.ops import AsExtOp

    @wasm_module(wasm_file)
    class MyWasm:
        @wasm
        def two(self: "MyWasm") -> int: ...

    @guppy
    def main() -> int:
        c = MyWasm(1)
        x = c.two()
        c.discard()
        return x

    mod = main.compile_function()
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
