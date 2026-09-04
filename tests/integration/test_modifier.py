import base64
from collections.abc import Callable
import pytest

from guppylang.decorator import guppy
from guppylang.defs import GuppyFunctionDefinition
from guppylang.std.array import array

from guppylang.std.builtins import (
    Controllable,
    Daggerable,
    Function,
    Unitary,
    control,
    dagger,
    owned,
    panic,
    power,
)
from guppylang.std.num import nat
from guppylang.std.quantum import (
    angle,
    cx,
    discard,
    h,
    measure,
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
    @guppy(daggerable=True)
    def foo(x: int) -> int:
        return x

    @guppy
    def main() -> None:
        q = qubit()
        c = qubit()
        y = 1
        with dagger:
            x = foo(y)
            h(q)
        with dagger:
            y = 2
            with control(c):
                h(q)

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


def test_power_simple(validate, use_experimental_features):
    @guppy
    def bar(n: nat) -> None:
        with power(n):
            pass

    # Tket passes reject power modifiers, so do not export this HUGR for CI
    # normalization and don't run default optimization passes.
    validate(
        bar.with_minimal_opt().compile_function(),
        export=False,
    )


def test_call_in_modifier(validate):
    @guppy(daggerable=True)
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
        with control(q), dagger:
            pass

    validate(bar.compile_function())


def test_nested_modifiers(validate):
    @guppy
    def bar(q: qubit) -> None:
        with control(q):
            with dagger:
                pass

    validate(bar.compile_function())


def test_panic_in_control(validate):
    @guppy
    def bar(q: qubit) -> None:
        with control(q):
            panic("a")

    validate(bar.compile_function())


def test_free_linear_variable_in_modifier(validate):
    T = guppy.type_var("T", copyable=False, droppable=False)

    @guppy(controllable=True)
    def use(a: T) -> None:
        pass

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

    @guppy
    def use(a: T) -> None:
        pass

    @guppy
    def bar(q: array[qubit, 3]) -> None:
        a = 3
        with control(q):
            use(a)

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


def test_nested_dagger_control(validate):
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
                f(q)

    apply_unitary.check()

    @guppy(unitary=True)
    def foo(q: qubit) -> None:
        pass

    @guppy
    def main(q1: qubit, q2: qubit) -> None:
        apply_unitary(h, q1, q2)
        apply_unitary(foo, q1, q2)

    validate(main.compile_function())


def test_custom_unitary_higher_order_callables(validate, use_experimental_features):
    """Custom modifier methods determine higher-order callable capabilities."""

    @guppy.unitary
    class custom_dagger:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def daggered(q: qubit) -> None:
            pass

    @guppy.unitary
    class custom_control:
        n = guppy.nat_var("n")

        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled(q: qubit, _controls: array[qubit, n]) -> None:
            pass

    @guppy.unitary
    class custom_unitary:
        n = guppy.nat_var("n")

        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def daggered(q: qubit) -> None:
            pass

        @guppy
        def controlled(q: qubit, _controls: array[qubit, n]) -> None:
            pass

        @guppy
        def ctrl_daggered(q: qubit, _controls: array[qubit, n]) -> None:
            pass

    @guppy.unitary
    class custom_call:
        @guppy
        def __call__(q: qubit) -> None:
            pass

    @guppy(daggerable=True)
    def apply_dagger(f: Daggerable[[qubit], None], q: qubit) -> None:
        f(q)

    @guppy(controllable=True)
    def apply_control(f: Controllable[[qubit], None], q: qubit) -> None:
        f(q)

    @guppy(unitary=True)
    def apply_unitary(f: Unitary[[qubit], None], q: qubit) -> None:
        f(q)

    @guppy
    def apply_plain(f: Function[[qubit], None], q: qubit) -> None:
        f(q)

    @guppy
    def apply_plain2(f: Callable[[qubit], None], q: qubit) -> None:
        f(q)

    @guppy
    def main(q: qubit) -> None:
        apply_dagger(custom_dagger, q)
        apply_control(custom_control, q)
        apply_unitary(custom_unitary, q)
        apply_plain(custom_dagger, q)
        apply_plain(custom_control, q)
        apply_plain(custom_unitary, q)
        apply_plain(custom_call, q)
        apply_plain2(custom_dagger, q)
        apply_plain2(custom_control, q)
        apply_plain2(custom_unitary, q)
        apply_plain2(custom_call, q)

    validate(main.compile_function())


def test_controlled_impl_is_executed(use_experimental_features, run_int_fn):
    @guppy.unitary
    class custom_gate:
        n = guppy.nat_var("n")

        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled(q: qubit, _controls: array[qubit, n]) -> None:
            x(q)

    @guppy
    def main() -> int:
        target = qubit()
        control_qubit = qubit()
        x(control_qubit)
        with control(control_qubit):
            custom_gate(target)
        result = measure(target).read()
        discard(control_qubit)
        return 1 if result else 0

    run_int_fn(main, expected=1, num_qubits=2)


def test_daggered_impl_is_executed(use_experimental_features, run_int_fn):
    @guppy.unitary
    class custom_gate:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def daggered(q: qubit) -> None:
            x(q)

    @guppy
    def main() -> int:
        target = qubit()
        with dagger:
            custom_gate(target)
        return 1 if measure(target).read() else 0

    run_int_fn(main, expected=1, num_qubits=1)


def test_ctrl_daggered_impl_is_executed(use_experimental_features, run_int_fn):
    @guppy.unitary
    class custom_gate:
        n = guppy.nat_var("n")

        @guppy(controllable=True)
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def ctrl_daggered(q: qubit, _controls: array[qubit, n]) -> None:
            x(q)

    @guppy
    def main() -> int:
        target = qubit()
        control_qubit = qubit()
        x(control_qubit)
        with control(control_qubit), dagger:
            custom_gate(target)
        result = measure(target).read()
        discard(control_qubit)
        return 1 if result else 0

    run_int_fn(main, expected=1, num_qubits=2)


def test_struct_custom_modifier_impls_are_executed(
    use_experimental_features, run_int_fn
):
    @guppy.struct(frozen=True)
    class CustomGates:
        enabled: bool

        @guppy.unitary
        class apply:
            n = guppy.nat_var("n")

            @guppy
            def __call__(self, q: qubit) -> None:
                pass

            @guppy
            def daggered(self, q: qubit) -> None:
                if self.enabled:
                    x(q)

            @guppy
            def controlled(
                self,
                q: qubit,
                _controls: array[qubit, n],
            ) -> None:
                if self.enabled:
                    x(q)

            @guppy
            def ctrl_daggered(
                self,
                q: qubit,
                _controls: array[qubit, n],
            ) -> None:
                if self.enabled:
                    x(q)

    @guppy
    def main_plain() -> int:
        target = qubit()
        CustomGates(True).apply(target)
        return 1 if measure(target).read() else 0

    @guppy
    def main_daggered() -> int:
        target = qubit()
        with dagger:
            CustomGates(True).apply(target)
        return 1 if measure(target).read() else 0

    @guppy
    def main_controlled() -> int:
        target = qubit()
        control_qubit = qubit()
        x(control_qubit)
        with control(control_qubit):
            CustomGates(True).apply(target)
        result = measure(target).read()
        discard(control_qubit)
        return 1 if result else 0

    @guppy
    def main_ctrl_daggered() -> int:
        target = qubit()
        control_qubit = qubit()
        x(control_qubit)
        with control(control_qubit), dagger:
            CustomGates(True).apply(target)
        result = measure(target).read()
        discard(control_qubit)
        return 1 if result else 0

    run_int_fn(main_plain, expected=0, num_qubits=1)
    run_int_fn(main_daggered, expected=1, num_qubits=1)
    run_int_fn(main_controlled, expected=1, num_qubits=2)
    run_int_fn(main_ctrl_daggered, expected=1, num_qubits=2)


def test_enum_custom_modifier_impls_are_executed(use_experimental_features, run_int_fn):
    @guppy.enum
    class CustomGates:
        Enabled = {}

        @guppy.unitary
        class apply:
            n = guppy.nat_var("n")

            @guppy
            def __call__(self, q: qubit) -> None:
                pass

            @guppy
            def daggered(self, q: qubit) -> None:
                x(q)

            @guppy
            def controlled(
                self,
                q: qubit,
                _controls: array[qubit, n],
            ) -> None:
                x(q)

            @guppy
            def ctrl_daggered(
                self,
                q: qubit,
                _controls: array[qubit, n],
            ) -> None:
                x(q)

    @guppy
    def apply_daggered(gates: CustomGates, target: qubit) -> None:
        with dagger:
            gates.apply(target)

    @guppy
    def apply_controlled(
        gates: CustomGates, control_qubit: qubit, target: qubit
    ) -> None:
        with control(control_qubit):
            gates.apply(target)

    @guppy
    def apply_ctrl_daggered(
        gates: CustomGates, control_qubit: qubit, target: qubit
    ) -> None:
        with control(control_qubit), dagger:
            gates.apply(target)

    @guppy
    def main_daggered() -> int:
        target = qubit()
        apply_daggered(CustomGates.Enabled(), target)
        return 1 if measure(target).read() else 0

    @guppy
    def main_controlled() -> int:
        target = qubit()
        control_qubit = qubit()
        x(control_qubit)
        apply_controlled(CustomGates.Enabled(), control_qubit, target)
        result = measure(target).read()
        discard(control_qubit)
        return 1 if result else 0

    @guppy
    def main_ctrl_daggered() -> int:
        target = qubit()
        control_qubit = qubit()
        x(control_qubit)
        apply_ctrl_daggered(CustomGates.Enabled(), control_qubit, target)
        result = measure(target).read()
        discard(control_qubit)
        return 1 if result else 0

    run_int_fn(main_daggered, expected=1, num_qubits=1)
    run_int_fn(main_controlled, expected=1, num_qubits=2)
    run_int_fn(main_ctrl_daggered, expected=1, num_qubits=2)


def test_two_control_counts_distinct_runtime(use_experimental_features, run_int_fn):
    @guppy.unitary
    class custom_gate:
        n = guppy.nat_var("n")

        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled(q: qubit, _controls: array[qubit, n]) -> None:
            x(q)

    @guppy
    def main() -> int:
        target_one = qubit()
        control_one = qubit()
        x(control_one)
        with control(control_one):
            custom_gate(target_one)

        target_two = qubit()
        control_two_a = qubit()
        control_two_b = qubit()
        x(control_two_a)
        x(control_two_b)
        controls_two = array(control_two_a, control_two_b)
        with control(controls_two):
            custom_gate(target_two)

        result_one = measure(target_one).read()
        result_two = measure(target_two).read()
        discard(control_one)
        discard_array(controls_two)
        return (1 if result_one else 0) + (2 if result_two else 0)

    run_int_fn(main, expected=3, num_qubits=5)


@pytest.mark.xfail(reason="Returning protocols not supported")
def test_return_callable_with_stronger_flags(validate):
    """Returning a callable with more flags than required is valid."""

    @guppy(daggerable=True)
    def dagger_only(q: qubit) -> None:
        pass

    @guppy
    def second_order(f: Daggerable[[qubit], None]) -> None:
        pass

    @guppy
    def return_plain() -> Function[[qubit], None]:
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
    def apply_plain(f: Function[[qubit], None], q: qubit) -> None:
        f(q)

    @guppy(daggerable=True)
    def apply_dagger(f: Daggerable[[qubit], None], q: qubit) -> None:
        f(q)

    @guppy
    def main(q: qubit) -> None:
        apply_plain(control_fun, q)
        apply_dagger(unitary_fun, q)

    validate(main.compile_function())


def test_double_dagger_cancellation_1(validate):
    """Two daggers in a single with-block cancel out: foo needs no dagger support."""

    @guppy.declare
    def foo(q: qubit) -> None: ...

    @guppy
    def bar(q: qubit) -> None:
        with dagger, dagger:
            foo(q)

    validate(bar.compile_function())


def test_double_dagger_cancellation_2(validate, use_experimental_features):
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

    main.check()
    # Tket passes reject power modifiers, so do not export this HUGR for CI
    # normalization.
    # validate(main.compile())


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
        with control(ctrl):
            with dagger:
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
        with dagger:
            foo(q1, q2)
        with control(ctrl):
            foo(q1, q2)

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
            ladder(qs)

        return q1

    validate(foo.compile_function())


@guppy
def ext_helper(q: qubit) -> None:
    x(q)


@guppy
def helper(q: qubit) -> None:
    h(q)


def test_custom_modifier(validate, use_experimental_features):

    @guppy.unitary
    class foo:
        n = guppy.nat_var("n")
        c = guppy.nat_var("c")

        @guppy
        def __call__(q1: array[qubit, n]) -> None:
            # since we have custom implementations of the modifiers, there are no
            # restrictions on the body of the function
            q = qubit()
            helper(q1[0])
            i = 10
            while i > 0:
                i -= 1
                h(q1[0])
            measure(q)

        @guppy
        def daggered(q1: array[qubit, n]) -> None:
            ext_helper(q1[0])

        @guppy
        def controlled(q1: array[qubit, n], _controls: array[qubit, c]) -> None:
            h(_controls[0])

        @guppy
        def ctrl_daggered(q1: array[qubit, n], _controls: array[qubit, c]) -> None:
            h(_controls[0])

    @guppy
    def main() -> None:
        qs = array(qubit(), qubit())
        c = qubit()
        with control(c):
            foo(qs)
        with dagger:
            foo(qs)
        with control(c), dagger:
            foo(qs)
        discard_array(qs)
        measure(c)

    # Test compilation with and without passes
    validate(main.with_minimal_opt().compile())
    validate(main.compile())


def test_hugr_stability():
    """Test that the Hugr representation of a function is stable across multiple
    compilations: https://github.com/Quantinuum/guppylang/issues/1905"""

    @guppy(unitary=True)
    def foo(q: qubit) -> None:
        h(q)
        with dagger:
            h(q)
        with dagger:
            h(q)

    @guppy
    def main() -> None:
        q1 = qubit()
        q2 = qubit()
        with dagger:
            foo(q1)
            with control(q1):
                foo(q2)
        cx(q1, q2)
        with control(q1):
            foo(q2)

        discard(q1)
        discard(q2)

    hashes = set()

    def compile_to_sig(guppy_func: GuppyFunctionDefinition) -> str:
        package = guppy_func.compile()
        http_data = package.to_bytes()
        return base64.b64encode(http_data).decode()[-10:]

    for _ in range(20):
        sig = compile_to_sig(main)
        hashes.add(sig)

    assert len(hashes) == 1


def test_std(validate):
    from guppylang.std.err import Result, ok
    from guppylang.std.option import Option

    y = 42

    n = guppy.nat_var("n")

    @guppy.comptime(daggerable=True)
    def test(r: Result[int, qubit] @ owned) -> tuple[float, Option[qubit]]:
        b = r.is_ok()
        e = r.into_either()
        b = e.is_right()
        o = e.try_into_right()
        b = o.is_some()
        return 1 + 2.0 - 3 * 4 // y, o

    @guppy(unitary=True)
    def f(controller: qubit, target: qubit) -> None:
        a = angle(1 / 3)
        with control(controller):
            rx(target, a)

    @guppy.comptime(daggerable=True)
    def test_arr() -> array[int, n]:
        x = array(y // y for i in range(n)).copy()
        return x

    @guppy
    def main() -> None:
        test_arr[3]()
        r = ok[int, qubit](42)
        _, oq = test(r)
        oq.unwrap_nothing()
        c = qubit()
        t = qubit()
        f(c, t)
        discard(c)
        discard(t)

    validate(main.compile())
