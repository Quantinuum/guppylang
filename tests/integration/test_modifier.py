from collections.abc import Callable

from guppylang.decorator import guppy
from guppylang.std.array import array

from guppylang.std.builtins import (
    Controllable,
    Daggerable,
    Unitary,
    control,
    dagger,
    owned,
    power,
)
from guppylang.std.num import nat
from guppylang.std.quantum import (
    angle,
    cx,
    discard,
    h,
    measure_array,
    qubit,
    rx,
    discard_array,
    x,
)


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


def test_subscript_dagger(validate):
    @guppy
    def main(array_qubits: array[qubit, 2]) -> None:
        with dagger:
            h(array_qubits[1])

    validate(main.compile_function())


def test_assignment_in_dagger(validate):
    @guppy
    def main() -> None:
        q = qubit()
        c = qubit()
        y = 1
        with dagger:
            x = 5
            rx(q, angle(1 / x))
        with dagger:
            y = 2
            with power(2), control(c):
                rx(q, angle(1 / y))

        discard(q)
        discard(c)

    validate(main.compile_function())


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


def test_control_subscript(validate):
    @guppy
    def bar(q: array[qubit, 3]) -> None:
        with control(q[0]):
            h(q[1])

    validate(bar.compile_function())


def test_control_subscript_allocated_array(validate):
    @guppy
    def bar() -> None:
        c = qubit()
        qs: array[qubit, 2] = array(qubit(), qubit())
        with control(qs[0], c):
            h(qs[1])

        discard_array(qs)
        discard(c)

    validate(bar.compile_function())


def test_multidimensional_control_subscript(validate):
    @guppy
    def main(qs: array[array[qubit, 2], 2], c: qubit) -> None:
        with control(qs[0]):
            h(qs[1][1])

    validate(main.compile_function())


def test_nested_element_control_subscript(validate):
    @guppy
    def main(qs: array[array[qubit, 2], 2], target: qubit) -> None:
        with control(qs[0][0]):
            h(target)

    validate(main.compile_function())


def test_3d_array_control_subscript(validate):
    @guppy
    def main(qs: array[array[array[qubit, 2], 2], 2], target: qubit) -> None:
        with control(qs[0][0][0]):
            h(target)

    validate(main.compile_function())


def test_4d_array_control_subscript(validate):
    @guppy
    def main(qs: array[array[array[array[qubit, 2], 2], 2], 2], target: qubit) -> None:
        with control(qs[0][0][0][0]):
            h(target)

    validate(main.compile_function())


def test_control_subscript_nested(validate):

    @guppy
    def f(array_controllers: array[qubit, 3], c: qubit) -> None:

        with control(array_controllers[0], c):
            h(array_controllers[1])
            with control(array_controllers[1]):
                h(array_controllers[2])

    @guppy
    def main() -> None:
        q = qubit()
        array_controllers: array[qubit, 3] = array(qubit(), qubit(), qubit())
        f(array_controllers, q)

        discard_array(array_controllers)
        discard(q)

    validate(main.compile())


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

    @guppy.declare(controllable=True)
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
    """Nested dagger+power: daggerable/unitary functions are valid
    (power adds no unitary flag)."""

    @guppy(daggerable=True)
    def foo_d(q: qubit) -> None:
        pass

    @guppy(unitary=True)
    def foo_u(q: qubit) -> None:
        pass

    @guppy
    def bar(q: qubit) -> None:
        with dagger:
            with power(2):
                foo_d(q)
                foo_u(q)

    validate(bar.compile_function())


def test_nested_control_dagger(validate):
    """Nested control+dagger: function supporting both flags is valid."""

    @guppy(controllable=True, daggerable=True)
    def foo_double(q: qubit) -> None:
        pass

    @guppy(unitary=True)
    def foo_u(q: qubit) -> None:
        pass

    @guppy
    def bar(ctrl: qubit, q: qubit) -> None:
        with control(ctrl):
            with dagger:
                foo_double(q)
                foo_u(q)

    validate(bar.compile_function())


def test_nested_power_control(validate):
    """Nested power+control: controllable/unitary functions are valid
    (power adds no unitary flag)."""

    @guppy(controllable=True)
    def foo_c(q: qubit) -> None:
        pass

    @guppy(unitary=True)
    def foo_u(q: qubit) -> None:
        pass

    @guppy
    def bar(ctrl: qubit, q: qubit) -> None:
        with power(2):
            with control(ctrl):
                foo_c(q)
                foo_u(q)

    validate(bar.compile_function())


def test_nested_triple_all_flags(validate):
    """Triple nesting with a function supporting all unitary flags is valid."""

    @guppy(daggerable=True, controllable=True)
    def foo_s(q: qubit) -> None:
        pass

    @guppy(unitary=True)
    def foo_u(q: qubit) -> None:
        pass

    @guppy
    def bar(ctrl: qubit, q: qubit) -> None:
        with dagger:
            with control(ctrl):
                with power(2):
                    foo_s(q)
                    foo_u(q)

    validate(bar.compile_function())


def test_higher_order_daggerable_callable(validate):
    """Higher-order arguments can require dagger support."""

    @guppy(daggerable=True)
    def apply_dagger(f: Daggerable[[qubit], None], q: qubit) -> None:
        f(q)

    @guppy
    def main(q: qubit) -> None:
        with dagger:
            apply_dagger(h, q)

    validate(main.compile_function())


def test_higher_order_control_controllable_callable(validate):
    """Higher-order arguments can require control support."""

    @guppy(controllable=True)
    def apply_control(f: Controllable[[qubit], None], ctrl: qubit, q: qubit) -> None:
        with control(ctrl):
            f(q)

    @guppy
    def main(ctrl: qubit, q: qubit) -> None:
        apply_control(h, ctrl, q)

    validate(main.compile_function())


def test_higher_order_unitary_callable(validate):
    """A unitary higher-order argument can be used in a combined modifier context."""

    @guppy(unitary=True)
    def apply_unitary(f: Unitary[[qubit], None], ctrl: qubit, q: qubit) -> None:
        with dagger:
            with control(ctrl):
                with power(2):
                    f(q)

    validate(apply_unitary.compile_function())


def test_return_callable_with_stronger_flags(validate):
    """Returning a callable with more flags than required is valid."""

    @guppy(daggerable=True)
    def dagger_only(q: qubit) -> None:
        pass

    @guppy
    def second_order(f: Daggerable[[qubit], None]) -> None:
        pass

    @guppy
    def return_plain() -> Callable[[qubit], None]:
        return dagger_only

    @guppy
    def return_daggerable() -> Daggerable[[qubit], None]:
        return h

    @guppy
    def main() -> None:
        second_order(return_daggerable())

    validate(return_plain.compile_function())
    validate(return_daggerable.compile_function())
    validate(main.compile_function())


def test_take_callable_taking_weaker_callable(validate):
    """Arguments weaker than the required callable flags."""

    @guppy(controllable=True)
    def control_fun(q: qubit) -> None:
        pass

    @guppy(unitary=True)
    def unitary_fun(q: qubit) -> None:
        pass

    @guppy
    def apply_plain(f: Callable[[qubit], None], q: qubit) -> None:
        f(q)

    @guppy(daggerable=True)
    def apply_dagger(f: Daggerable[[qubit], None], q: qubit) -> None:
        f(q)

    @guppy
    def take_plain_consumer(
        consumer: Callable[[Callable[[qubit], None], qubit], None], q: qubit
    ) -> None:
        consumer(control_fun, q)

    @guppy
    def take_daggerable_consumer(
        consumer: Callable[[Daggerable[[qubit], None], qubit], None], q: qubit
    ) -> None:
        consumer(unitary_fun, q)

    @guppy
    def main(q: qubit) -> None:
        take_plain_consumer(apply_dagger, q)
        take_daggerable_consumer(apply_plain, q)
        apply_plain(control_fun, q)
        apply_dagger(unitary_fun, q)

    validate(main.compile_function())


def test_nested_same_modifier(validate):
    """Double-nesting the same modifier (dagger) with a dagger-supporting function."""

    @guppy(daggerable=True)
    def foo(q: qubit) -> None:
        pass

    @guppy
    def bar(q: qubit) -> None:
        with dagger:
            with dagger:
                foo(q)

    validate(bar.compile_function())


def test_double_dagger_cancellation_1(validate):
    """Two daggers in a single with-block cancel out: foo needs no dagger support."""

    @guppy.declare
    def foo(q: qubit) -> None: ...

    @guppy
    def bar(q: qubit) -> None:
        with dagger, dagger:
            foo(q)

    validate(bar.compile_function())


def test_double_dagger_cancellation_2(validate):
    @guppy(controllable=True)
    def not_dagger_func(q: qubit) -> None:
        pass

    @guppy
    def main() -> None:
        q = qubit()
        c2 = qubit()
        with dagger:
            with control(c2):
                with dagger:
                    with power(3):
                        not_dagger_func(q)

        discard(q)
        discard(c2)

    validate(main.compile())


def test_combined_with_items_nested(validate):
    """Multiple modifiers in one with-block are all propagated into a nested block."""

    @guppy(daggerable=True, controllable=True)
    def foo(q: qubit) -> None:
        pass

    @guppy(unitary=True)
    def foo_u(q: qubit) -> None:
        pass

    @guppy
    def bar(ctrl: qubit, q: qubit) -> None:
        with control(ctrl), dagger:
            with power(2):
                foo(q)
                foo_u(q)

    validate(bar.compile_function())


def test_comptime_dagger(validate):
    """Comptime function with daggerable=True can be called inside a dagger block."""

    @guppy.comptime(daggerable=True)
    def foo(q: qubit) -> None:
        h(q)

    @guppy
    def bar(q: qubit) -> None:
        with dagger:
            foo(q)

    validate(bar.compile_function())


def test_comptime_control(validate):
    """Comptime function with controllable=True can be called inside a control block."""

    @guppy.comptime(controllable=True)
    def foo(q: qubit) -> None:
        h(q)

    @guppy
    def bar(ctrl: qubit, q: qubit) -> None:
        with control(ctrl):
            foo(q)

    validate(bar.compile_function())


def test_comptime_unitary(validate):
    """Comptime function with unitary=True supports all modifier contexts."""

    @guppy.comptime(unitary=True)
    def foo(q1: qubit, q2: qubit) -> None:
        cx(q1, q2)
        h(q1)

    @guppy
    def bar(ctrl: qubit, q1: qubit, q2: qubit) -> None:
        with power(2):
            foo(q1, q2)
        with dagger:
            foo(q1, q2)
        with control(ctrl):
            foo(q1, q2)

    validate(bar.compile_function())


def test_comptime_unitary_combined_modifiers(validate):
    """Comptime unitary function called inside combined modifier block."""

    @guppy.comptime(unitary=True)
    def foo(q: qubit) -> None:
        h(q)

    @guppy
    def bar(ctrl: qubit, q: qubit) -> None:
        with control(ctrl), dagger:
            with power(2):
                foo(q)

    validate(bar.compile_function())


def test_comptime_unitary_mixed(validate):
    """Regular unitary and comptime unitary functions used together with modifiers."""

    @guppy.comptime(unitary=True)
    def ladder(qs: array[qubit, 10]) -> None:
        for q1, q2 in zip(qs[1:], qs[:-1]):
            cx(q1, q2)

    @guppy
    def foo(qs: array[qubit, 10]) -> qubit:
        q1 = qubit()

        with control(q1), dagger:
            with power(2):
                ladder(qs)

        return q1

    validate(foo.compile_function())


def test_custom_modifier(validate):

    @guppy.unitary
    class foo:
        n = guppy.nat_var("n")
        c = guppy.nat_var("c")

        @guppy
        def __call__(q1: array[qubit, n]) -> None:
            h(q1[0])

        @guppy
        def call_daggered(q1: array[qubit, n]) -> None:
            h(q1[0])

        @guppy
        def call_controlled(q1: array[qubit, n], _controls: array[qubit, c]) -> None:
            h(_controls[0])

        @guppy
        def call_ctrl_daggered(q1: array[qubit, n], _controls: array[qubit, c]) -> None:
            h(_controls[0])

    @guppy
    def main() -> None:
        q1 = array(qubit())
        foo(q1)
        measure_array(q1)

    package = main.check()
    # NICOLA: TODO after Mark
    # hugr_module = package.modules[0]
    # for _, data in hugr_module.nodes():
    #     if (
    #         isinstance(data.op, FuncDefn)
    #         and data.op.f_name == "__main__.foo.__call__$1"
    #     ):
    #         assert data.metadata[DAGGERED_KEY] == "__main__.foo.call_daggered$1"
    #         assert data.metadata[CONTROLLED_KEY] == "__main__.foo.call_controlled$1"
    #         assert (
    #             data.metadata[CTRL_DAGGERED_KEY] == "__main__.foo.call_ctrl_daggered$1"  # noqa: E501
    #         )


# NICOLA: TODO investigate why this cannot be inside test_use_other_functions
@guppy
def ext_helper(q: qubit) -> None:
    x(q)


def test_use_other_functions(validate):
    # NICOLA: TODO make the custom metod generic on control size

    @guppy.unitary
    class foo:
        @guppy
        def helper(q: qubit) -> None:
            h(q)

        @guppy
        def __call__(q: qubit) -> None:
            helper(q)  # noqa: F821
            ext_helper(q)

        @guppy
        def call_daggered(q: qubit) -> None:
            helper(q)  # noqa: F821
            ext_helper(q)

        @guppy
        def call_controlled(q: qubit, _controls: array[qubit, 1]) -> None:
            helper(q)  # noqa: F821
            helper(_controls[0])  # noqa: F821
            ext_helper(q)

        @guppy
        def call_ctrl_daggered(q: qubit, _controls: array[qubit, 1]) -> None:
            helper(q)  # noqa: F821
            helper(_controls[0])  # noqa: F821
            ext_helper(q)

    @guppy
    def main() -> None:
        q = qubit()
        foo(q)
        discard(q)

    validate(main.compile())
