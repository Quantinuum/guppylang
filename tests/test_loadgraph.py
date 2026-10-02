import pytest
from guppylang import guppy
from guppylang.std.builtins import Function, owned
from guppylang_internals.analysis.callgraph import CallGraph
from guppylang_internals.analysis.effects import compute_effects
from guppylang_internals.engine import ENGINE
from guppylang_internals.tys.arg import TypeArg
from guppylang_internals.tys.builtin import float_type, int_type


def test_function_values():
    @guppy
    def assigned() -> int:
        return 1

    @guppy
    def passed() -> int:
        return 2

    @guppy
    def returned() -> int:
        return 3

    @guppy
    def consume(f: Function[[], int]) -> int:
        return f()

    @guppy
    def root() -> Function[[], int]:
        f = assigned
        alias = f
        alias()
        consume(passed)
        consume(passed)
        return returned

    root.check()

    assert ENGINE.load_graph[root.id, ()] == {
        (assigned.id, ()),
        (passed.id, ()),
        (returned.id, ()),
    }
    assert ENGINE.load_graph[consume.id, ()] == set()
    assert ENGINE.load_graph[assigned.id, ()] == set()
    assert (consume.id, ()) in ENGINE.call_graph[root.id, ()]
    assert (passed.id, ()) not in ENGINE.call_graph[root.id, ()]


def test_direct_calls_do_not_load():
    @guppy
    def leaf() -> int:
        return 1

    @guppy
    def root() -> int:
        leaf()  # Synthesized call.
        return leaf()  # Call checked against the return type.

    root.check()

    assert ENGINE.load_graph[root.id, ()] == set()
    assert (leaf.id, ()) in ENGINE.call_graph[root.id, ()]


def test_arguments_of_nested_calls_are_values():
    @guppy
    def leaf() -> int:
        return 1

    @guppy
    def factory(f: Function[[], int]) -> Function[[], int]:
        return f

    @guppy
    def root() -> int:
        factory(leaf)()
        return factory(leaf)()

    root.check()

    assert ENGINE.load_graph[root.id, ()] == {(leaf.id, ())}
    assert ENGINE.load_graph[factory.id, ()] == set()


@pytest.mark.parametrize("type_kind", ["struct", "enum"])
@pytest.mark.parametrize("use", ["assigned", "passed", "returned", "called"])
def test_bound_methods(type_kind, use):
    type_decorator = guppy.struct(frozen=True) if type_kind == "struct" else guppy.enum

    @type_decorator
    class Example:
        @guppy
        def method(self) -> int:
            return 1

    @guppy
    def consume(f: Function[[], int]) -> int:
        return f()

    @guppy
    def assigned(x: Example) -> int:
        f = x.method
        return f()

    @guppy
    def passed(x: Example) -> int:
        return consume(x.method)

    @guppy
    def returned(x: Example) -> Function[[], int]:
        return x.method

    @guppy
    def called(x: Example) -> int:
        x.method()
        return x.method()

    root = {
        "assigned": assigned,
        "passed": passed,
        "returned": returned,
        "called": called,
    }[use]
    root.check()

    method = ENGINE.get_type_member(ENGINE.get_parsed(Example.id), "method")
    assert method is not None
    assert ENGINE.load_graph[root.id, ()] == (
        set() if use == "called" else {(method, ())}
    )


@pytest.mark.parametrize("type_kind", ["struct", "enum"])
def test_static_methods(type_kind):
    type_decorator = guppy.struct(frozen=True) if type_kind == "struct" else guppy.enum

    @type_decorator
    class Example:
        @guppy
        @staticmethod
        def loaded() -> int:
            return 1

        @guppy
        @staticmethod
        def called() -> int:
            return 2

    @guppy
    def root(x: Example) -> Function[[], int]:
        f = Example.loaded
        f()
        Example.called()
        x.called()
        return x.loaded

    root.check()

    loaded = ENGINE.get_type_member(ENGINE.get_parsed(Example.id), "loaded")
    assert loaded is not None
    assert ENGINE.load_graph[root.id, ()] == {(loaded, ())}


@pytest.mark.parametrize("use", ["bare", "explicit", "inferred", "called"])
def test_generic_functions(use):
    @guppy
    def identity[T](x: T @ owned) -> T:
        return x

    @guppy
    def bare() -> int:
        f = identity
        return f(1)

    @guppy
    def explicit() -> Function[[int], int]:
        f = identity[float]
        f(1.0)
        return identity[int]

    @guppy
    def inferred() -> Function[[int], int]:
        f: Function[[float], float] = identity
        f(1.0)
        return identity

    @guppy
    def called() -> int:
        identity[int](1)
        identity(1.0)
        return identity[int](1)

    root = {
        "bare": bare,
        "explicit": explicit,
        "inferred": inferred,
        "called": called,
    }[use]
    root.check()

    defn = ENGINE.get_parsed(identity.id)
    generic = (identity.id, tuple(param.to_bound() for param in defn.params))
    if use == "called":
        expected = set()
    elif use == "bare":
        expected = {generic}
    else:
        expected = {
            generic,
            (identity.id, (TypeArg(int_type()),)),
            (identity.id, (TypeArg(float_type()),)),
        }
    assert ENGINE.load_graph[root.id, ()] == expected


def test_nested_function_owns_its_loads():
    @guppy
    def leaf() -> int:
        return 1

    @guppy
    def outer() -> Function[[], int]:
        @guppy
        def inner() -> Function[[], int]:
            return leaf

        return inner()

    outer.check()

    [inner] = ENGINE.call_graph[outer.id, ()]
    assert ENGINE.load_graph[outer.id, ()] == set()
    assert ENGINE.load_graph[inner] == {(leaf.id, ())}


@pytest.mark.parametrize("type_kind", ["struct", "enum"])
def test_generic_bound_method(type_kind):
    type_decorator = guppy.struct(frozen=True) if type_kind == "struct" else guppy.enum

    @type_decorator
    class Example:
        @guppy
        def method[T](self, x: T @ owned) -> T:
            return x

    @guppy
    def root(x: Example) -> Function[[int], int]:
        f = x.method[float]
        f(1.0)
        x.method[int](1)
        return x.method[int]

    @guppy
    def called(x: Example) -> int:
        x.method[float](1.0)
        return x.method[int](1)

    called.check()
    assert ENGINE.load_graph[called.id, ()] == set()

    root.check()

    method = ENGINE.get_type_member(ENGINE.get_parsed(Example.id), "method")
    assert method is not None
    defn = ENGINE.get_parsed(method)
    assert ENGINE.load_graph[root.id, ()] == {
        (method, tuple(param.to_bound() for param in defn.params)),
        (method, (TypeArg(int_type()),)),
        (method, (TypeArg(float_type()),)),
    }


def test_generic_loads_follow_owner_specialization():
    @guppy
    def identity[T](x: T @ owned) -> T:
        return x

    @guppy
    def loader[T](x: T @ owned) -> tuple[T, Function[[T @ owned], T]]:
        return x, identity[T]

    @guppy
    def root() -> None:
        loader(1)
        loader(1.0)

    root.check()

    defn = ENGINE.get_parsed(identity.id)
    generic = (identity.id, tuple(param.to_bound() for param in defn.params))
    for ty in (int_type(), float_type()):
        inst = (TypeArg(ty),)
        assert ENGINE.load_graph[loader.id, inst] == {generic, (identity.id, inst)}


def test_declaration_load_and_reset():
    @guppy.declare
    def external() -> int: ...

    @guppy
    def root() -> Function[[], int]:
        return external

    root.check()

    assert ENGINE.load_graph[root.id, ()] == {(external.id, ())}
    assert (external.id, ()) not in ENGINE.load_graph
    ENGINE.reset()
    assert ENGINE.load_graph == {}


def test_loads_do_not_propagate_call_effects():
    from guppylang.std.builtins import panic

    @guppy
    def leaf() -> None:
        panic("only happens when called")

    @guppy
    def root() -> Function[[], None]:
        return leaf

    root.check()

    effects = compute_effects(CallGraph(ENGINE.call_graph), ENGINE.func_effects)
    assert ENGINE.load_graph[root.id, ()] == {(leaf.id, ())}
    assert effects[root.id, ()] == frozenset()
    assert effects[leaf.id, ()]


def test_loads_in_containers_and_generic_owners():
    @guppy
    def leaf() -> int:
        return 1

    @guppy
    def generic[T](x: T @ owned) -> tuple[T, Function[[], int]]:
        fs = (leaf, leaf)
        f, _ = fs
        return x, f

    @guppy
    def root() -> None:
        generic(1)
        generic(1.0)

    root.check()

    assert ENGINE.load_graph[root.id, ()] == set()
    owners = [mono for mono in ENGINE.load_graph if mono[0] == generic.id]
    assert len(owners) >= 2
    assert all(ENGINE.load_graph[owner] == {(leaf.id, ())} for owner in owners)


def test_constructor_references():
    @guppy.struct(frozen=True)
    class Struct:
        pass

    @guppy.enum
    class Enum:
        Variant = {}  # noqa: RUF012 - Guppy enum variant declaration.

    @guppy
    def calls() -> None:
        Struct()
        Enum.Variant()

    @guppy
    def loads() -> tuple[Function[[], Struct], Function[[], Enum]]:
        return Struct, Enum.Variant

    calls.check()
    assert ENGINE.load_graph[calls.id, ()] == set()

    loads.check()
    struct_constructor = ENGINE.get_type_member(ENGINE.get_parsed(Struct.id), "__new__")
    enum_constructor = ENGINE.get_type_member(ENGINE.get_parsed(Enum.id), "Variant")
    assert struct_constructor is not None
    assert enum_constructor is not None
    assert ENGINE.load_graph[loads.id, ()] == {
        (struct_constructor, ()),
        (enum_constructor, ()),
    }
