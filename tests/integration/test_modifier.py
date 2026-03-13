from guppylang.decorator import guppy
from guppylang.std.quantum import qubit
from guppylang.std.num import nat
from guppylang.std.builtins import owned
from guppylang.std.array import array

# Dummy variables to suppress Undefined name
# TODO: `ruff` fails when without these, which need to be fixed
dagger = object()
control = object()
power = object()


def test_dagger_simple(validate):
    @guppy
    def bar() -> None:
        with dagger:
            pass

    validate(bar.compile_function())


def test_dagger_call_simple(validate):
    @guppy
    def bar() -> None:
        with dagger():
            pass

    validate(bar.compile_function())


def test_control_simple(validate):
    @guppy
    def bar(q: qubit) -> None:
        with control(q):
            pass

    validate(bar.compile_function())


def test_control_multiple(validate):
    @guppy
    def bar(q1: qubit, q2: qubit) -> None:
        with control(q1, q2):
            pass

    validate(bar.compile_function())


def test_control_array(validate):
    @guppy
    def bar(q: array[qubit, 3]) -> None:
        with control(q):
            pass

    validate(bar.compile_function())


def test_power_simple(validate):
    @guppy
    def bar(n: nat) -> None:
        with power(n):
            pass

    validate(bar.compile_function())


def test_call_in_modifier(validate):
    @guppy
    def foo() -> None:
        pass

    @guppy
    def bar() -> None:
        with dagger:
            foo()

    validate(bar.compile_function())


def test_combined_modifiers(validate):
    @guppy
    def bar(q: qubit) -> None:
        with control(q), power(2), dagger:
            pass

    validate(bar.compile_function())


def test_nested_modifiers(validate):
    @guppy
    def bar(q: qubit) -> None:
        with control(q):
            with power(2):
                with dagger:
                    pass

    validate(bar.compile_function())


def test_free_linear_variable_in_modifier(validate):
    T = guppy.type_var("T", copyable=False, droppable=False)

    @guppy.declare(control=True)
    def use(a: T) -> None: ...

    @guppy.declare
    def discard(a: T @ owned) -> None: ...

    @guppy
    def bar(q: qubit) -> None:
        a = array(qubit())
        with control(q):
            use(a)
        discard(a)

    validate(bar.compile_function())


def test_free_copyable_variable_in_modifier(validate):
    T = guppy.type_var("T", copyable=True, droppable=True)

    @guppy.declare
    def use(a: T) -> None: ...

    @guppy
    def bar(q: array[qubit, 3]) -> None:
        a = 3
        with control(q):
            use(a)

    validate(bar.compile_function())


def test_nested_dagger_power(validate):
    """Nested dagger+power: function supporting both flags is valid."""

    @guppy(dagger=True, power=True)
    def foo(q: qubit) -> None:
        pass

    @guppy
    def bar(q: qubit) -> None:
        with dagger:
            with power(2):
                foo(q)

    validate(bar.compile_function())


def test_nested_control_dagger(validate):
    """Nested control+dagger: function supporting both flags is valid."""

    @guppy(control=True, dagger=True)
    def foo(q: qubit) -> None:
        pass

    @guppy
    def bar(ctrl: qubit, q: qubit) -> None:
        with control(ctrl):
            with dagger:
                foo(q)

    validate(bar.compile_function())


def test_nested_power_control(validate):
    """Nested power+control: function supporting both flags is valid."""

    @guppy(power=True, control=True)
    def foo(q: qubit) -> None:
        pass

    @guppy
    def bar(ctrl: qubit, q: qubit) -> None:
        with power(2):
            with control(ctrl):
                foo(q)

    validate(bar.compile_function())


def test_nested_triple_all_flags(validate):
    """Triple nesting with a function supporting all unitary flags is valid."""

    @guppy(dagger=True, control=True, power=True)
    def foo(q: qubit) -> None:
        pass

    @guppy
    def bar(ctrl: qubit, q: qubit) -> None:
        with dagger:
            with control(ctrl):
                with power(2):
                    foo(q)

    validate(bar.compile_function())


def test_nested_same_modifier(validate):
    """Double-nesting the same modifier (dagger) with a dagger-supporting function."""

    @guppy(dagger=True)
    def foo(q: qubit) -> None:
        pass

    @guppy
    def bar(q: qubit) -> None:
        with dagger:
            with dagger:
                foo(q)

    validate(bar.compile_function())


def test_double_dagger_cancellation(validate):
    """Two daggers in a single with-block cancel out: foo needs no dagger support."""

    @guppy.declare
    def foo(q: qubit) -> None: ...

    @guppy
    def bar(q: qubit) -> None:
        with dagger, dagger:
            foo(q)

    validate(bar.compile_function())


def test_combined_with_items_nested(validate):
    """Multiple modifiers in one with-block are all propagated into a nested block."""

    @guppy(dagger=True, control=True, power=True)
    def foo(q: qubit) -> None:
        pass

    @guppy
    def bar(ctrl: qubit, q: qubit) -> None:
        with control(ctrl), dagger:
            with power(2):
                foo(q)

    validate(bar.compile_function())


def test_triple_dagger(validate):
    """Three daggers: odd count means dagger context is still active."""

    @guppy(dagger=True)
    def foo(q: qubit) -> None:
        pass

    @guppy
    def bar(q: qubit) -> None:
        with dagger, dagger, dagger:
            foo(q)

    validate(bar.compile_function())


def test_double_dagger_cancel_nested_power(validate):
    """Cancelled daggers in outer block don't impose dagger constraint on nested."""

    @guppy(power=True)
    def foo(q: qubit) -> None:
        pass

    @guppy
    def bar(q: qubit) -> None:
        with dagger, dagger:
            with power(2):
                foo(q)

    validate(bar.compile_function())
