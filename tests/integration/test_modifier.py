import base64
from collections.abc import Callable
import pytest
from pytket.circuit import Circuit, Op, OpType, QControlBox

from guppylang.decorator import guppy
from guppylang.defs import GuppyFunctionDefinition
from guppylang.std.array import array

from guppylang.std.builtins import (
    Controllable,
    Daggerable,
    Function,
    Unitary,
    comptime,
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
    ry,
    rz,
    s,
    sdg,
    t,
    tdg,
    toffoli,
    v,
    vdg,
    discard_array,
    x,
    y,
    z,
)

c = guppy.nat_var("c")


def test_dagger_simple(validate):
    @guppy
    def bar() -> None:
        with dagger:
            pass

    validate(bar.compile_function())


def test_dagger_multiple_gates(run_statevector_fn):
    @guppy(daggerable=True)
    def prepare(q: qubit) -> None:
        rx(q, angle(0.25))
        rz(q, angle(0.25))

    @guppy
    def main() -> array[qubit, 1]:
        q = qubit()
        prepare(q)
        with dagger:
            prepare(q)
        return array(q)

    run_statevector_fn(main, expected=[1, 0], num_qubits=1)


@pytest.mark.parametrize(
    "gate",
    [h, x, y, z, s, sdg, t, tdg, v, vdg],
    ids=["h", "x", "y", "z", "s", "sdg", "t", "tdg", "v", "vdg"],
)
def test_dagger_gate(gate, run_statevector_fn):
    @guppy
    def main() -> array[qubit, 2]:
        q = qubit()
        ref = qubit()
        # Use a Bell pair so relative phase errors are observable.
        h(ref)
        cx(ref, q)

        gate(q)
        with dagger:
            gate(q)

        cx(ref, q)
        h(ref)
        return array(q, ref)

    run_statevector_fn(main, expected=[1, 0, 0, 0], num_qubits=2)


@pytest.mark.parametrize("gate", [rx, ry, rz], ids=["rx", "ry", "rz"])
def test_dagger_rotation(gate, run_statevector_fn):
    @guppy
    def main() -> array[qubit, 2]:
        q = qubit()
        ref = qubit()
        h(ref)
        cx(ref, q)

        gate(q, angle(0.25))
        with dagger:
            gate(q, angle(0.25))

        cx(ref, q)
        h(ref)
        return array(q, ref)

    run_statevector_fn(main, expected=[1, 0, 0, 0], num_qubits=2)


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


@pytest.mark.parametrize(
    ("gate", "op_type", "num_controls"),
    [
        pytest.param(gate, op_type, count, id=f"{op_type.name}-{count}-controls")
        for gate, op_type in [
            (y, OpType.Y),
            (z, OpType.Z),
            (h, OpType.H),
            (rx, OpType.Rx),
            (ry, OpType.Ry),
            (rz, OpType.Rz),
        ]
        for count in (1, 2)
    ],
)
def test_controlled_gate(gate, op_type, num_controls, run_statevector_fn):
    is_rotation = op_type in (OpType.Rx, OpType.Ry, OpType.Rz)
    op = Op.create(op_type, 0.25) if is_rotation else Op.create(op_type)
    num_qubits = num_controls + 1

    if is_rotation:

        @guppy(controllable=True)
        def apply_gate(q: qubit) -> None:
            gate(q, angle(0.25))

    else:

        @guppy(controllable=True)
        def apply_gate(q: qubit) -> None:
            gate(q)

    @guppy
    def main() -> array[qubit, num_qubits]:
        controls = array(qubit() for _ in range(num_controls))
        target = qubit()
        # Include active and inactive control sectors coherently. Prepare a
        # target that is not an eigenstate of any of the gates under test.
        for i in range(num_controls):
            h(controls[i])
        rx(target, angle(0.25))
        rz(target, angle(0.25))

        with control(controls):
            apply_gate(target)

        return controls.concat(array(target))

    expected = Circuit(num_qubits)
    for i in range(num_controls):
        expected.H(i)
    expected.Rx(0.25, num_controls)
    expected.Rz(0.25, num_controls)
    expected.add_qcontrolbox(QControlBox(op, num_controls), list(range(num_qubits)))

    run_statevector_fn(
        main, expected=expected.get_statevector().tolist(), num_qubits=num_qubits
    )


def test_controlled_toffoli(run_statevector_fn):
    # X with two controls, or CX with one extra control, is Toffoli.
    # One further control exercises their shared recursive decomposition.
    @guppy
    def main() -> array[qubit, 4]:
        ctrl = qubit()
        a = qubit()
        b = qubit()
        target = qubit()
        h(ctrl)
        h(a)
        h(b)

        with control(ctrl):
            toffoli(a, b, target)

        return array(ctrl, a, b, target)

    expected = Circuit(4)
    expected.H(0).H(1).H(2)
    expected.add_qcontrolbox(QControlBox(Op.create(OpType.CCX), 1), [0, 1, 2, 3])

    run_statevector_fn(main, expected=expected.get_statevector().tolist(), num_qubits=4)


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


def test_control_generic_function_call(validate):
    @guppy
    def generic_function[T](x: T) -> None:
        pass

    @guppy
    def controlled_generic_call[T](x: T) -> None:
        q = qubit()

        with control(q):
            generic_function(x)

        discard(q)

    @guppy
    def main() -> None:
        controlled_generic_call(1)

    validate(main.compile_function())


def test_control_generic_function_call_non_copyable(validate):
    @guppy(controllable=True)
    def generic_function[T](x: T) -> None:
        pass

    @guppy
    def controlled_generic_call[T](x: T) -> None:
        q = qubit()

        with control(q):
            generic_function(x)

        discard(q)

    @guppy
    def main() -> None:
        q = qubit()
        # a qubit is non-copyable, so the captured input must remain Inout.
        controlled_generic_call(q)
        discard(q)

    validate(main.compile_function())


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


def test_power_reassign_outer_before_use(validate):
    @guppy
    def main(x: int, b: bool, q: qubit) -> int:
        z = 0
        with power(2):
            with control(q):
                if b:
                    x = 1
                    y = x + z
        x = 3
        return x

    validate(main.compile_function())


def test_power_combined_modifiers(validate):
    @guppy
    def main(q: qubit, ctrl: qubit, n: nat, m: nat) -> None:
        with power(n), control(ctrl), dagger, power(m):
            rx(q, angle(0.25))

        with control(ctrl):
            a = angle(0.25)
            with power(n):
                with dagger:
                    with power(m):
                        rx(q, a)

    validate(main.compile_function())


@pytest.mark.parametrize(
    ("n", "m", "enabled"),
    [(0, 2, 1), (2, 0, 1), (2, 2, 1), (2, 3, 1), (2, 3, 0)],
)
def test_power_nested_repeats_block(n, m, enabled, run_statevector_fn):
    @guppy
    def main(outer: int, inner: int, enabled: int) -> array[qubit, 2]:
        q = qubit()
        ctrl = qubit()
        if enabled != 0:
            x(ctrl)
        with power(nat(outer)):
            with control(ctrl):
                with power(nat(inner)):
                    rx(q, angle(0.25))
                    rz(q, angle(0.125))
        if enabled != 0:
            for _ in range(outer * inner):
                rz(q, angle(-0.125))
                rx(q, angle(-0.25))
        return array(q, ctrl)

    # Four or six blocks leave a superposition; reversing the gate order and
    # angles returns |0>. With control disabled, both operations are skipped.
    run_statevector_fn(
        main, expected=[1 - enabled, enabled, 0, 0], args=[n, m, enabled], num_qubits=2
    )


def test_power_repeats_custom_daggered(run_statevector_fn):
    @guppy.unitary
    class custom_gate:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def daggered(q: qubit) -> None:
            rx(q, angle(-0.25))

    @guppy
    def main() -> array[qubit, 1]:
        q = qubit()
        rx(q, angle(0.5))
        with power(2), dagger:
            custom_gate(q)
        return array(q)

    run_statevector_fn(main, expected=[1, 0], num_qubits=1)


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


def test_custom_unitary_higher_order_callables(validate):
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
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
            pass

    @guppy.unitary
    class custom_unitary:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def daggered(q: qubit) -> None:
            pass

        @guppy
        def controlled[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
            pass

        @guppy
        def ctrl_daggered[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
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


def test_unitary_capture_local_variable(validate):

    def make_gate(theta: float):
        from guppylang.std.angles import angle as local_angle

        @guppy.unitary
        class gate:
            @guppy
            def __call__(q: qubit) -> None:
                rz(q, local_angle(comptime(theta)))

        return gate

    gate = make_gate(0.5)

    @guppy
    def main(q: qubit) -> None:
        gate(q)

    validate(main.compile_function())


def test_unitary_capture_external_method(validate):
    def make_gate():
        @guppy
        def controlled_impl(control_q: qubit, target_q: qubit) -> None:
            cx(control_q, target_q)

        @guppy
        def call_impl(q: qubit) -> None:
            pass

        @guppy.unitary
        class generated_gate:
            @guppy
            def __call__(target_q: qubit) -> None:
                x(target_q)
                call_impl(target_q)

            @guppy
            def controlled[n: nat](target_q: qubit, controls: array[qubit, n]) -> None:
                controlled_impl(controls[0], target_q)

        return generated_gate

    gate = make_gate()

    @guppy
    def main(q: qubit, c: qubit) -> None:
        gate(q)

    @guppy
    def main_controlled(q: qubit, c: qubit) -> None:
        with control(c):
            gate(q)

    validate(main.compile_function(), name="plain")
    validate(main_controlled.compile_function(), name="controlled")


def test_controlled_impl_is_executed(run_int_fn):
    @guppy.unitary
    class custom_gate:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
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


def test_controlled_impl_through_higher_order_call_is_executed(run_int_fn):
    """Control is propagated through higher order function calls."""

    @guppy.unitary
    class custom_gate:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
            x(q)

    @guppy(controllable=True)
    def apply(f: Controllable[[qubit], None], q: qubit) -> None:
        f(q)

    @guppy
    def main() -> int:
        target = qubit()
        control_qubit = qubit()
        x(control_qubit)
        with control(control_qubit):
            apply(custom_gate, target)
        result = measure(target).read()
        discard(control_qubit)
        return 1 if result else 0

    # The custom controlled body flips the target; the empty base body cannot do so.
    run_int_fn(main, expected=1, num_qubits=2)


def test_controlled_impl_through_helper_is_executed(run_int_fn):
    """A propagated control selects a custom implementation through a helper."""

    @guppy.unitary
    class custom_gate:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
            x(q)

    @guppy(controllable=True)
    def helper(q: qubit) -> None:
        custom_gate(q)

    @guppy
    def main() -> int:
        target = qubit()
        control_qubit = qubit()
        x(control_qubit)
        # `helper` has no custom controlled implementation. Its compiler-generated
        # control must propagate to the direct call of `custom_gate` in its body.
        with control(control_qubit):
            helper(target)
        result = measure(target).read()
        discard(control_qubit)
        return 1 if result else 0

    # Only custom_gate.controlled flips the target; its base implementation is empty.
    run_int_fn(main, expected=1, num_qubits=2)


def test_daggered_impl_is_executed(run_int_fn):
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


def test_ctrl_daggered_impl_is_executed(run_int_fn):
    @guppy.unitary
    class custom_gate:
        @guppy(unitary=True)
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def ctrl_daggered[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
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


@pytest.mark.parametrize("modifier", ["controlled", "daggered", "ctrl_daggered"])
def test_custom_modifier_in_loaded_function_is_executed(modifier, run_int_fn):
    """Indirect calls to loaded functions execute their custom modified methods."""

    @guppy.unitary
    class custom_gate:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
            x(q)

        @guppy
        def daggered(q: qubit) -> None:
            x(q)

        @guppy
        def ctrl_daggered[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
            x(q)

    @guppy
    def call_controlled(q: qubit, c: qubit) -> None:
        with control(c):
            custom_gate(q)

    @guppy
    def call_daggered(q: qubit, c: qubit) -> None:
        with dagger:
            custom_gate(q)

    @guppy
    def call_ctrl_daggered(q: qubit, c: qubit) -> None:
        with control(c), dagger:
            custom_gate(q)

    loaded = {
        "controlled": call_controlled,
        "daggered": call_daggered,
        "ctrl_daggered": call_ctrl_daggered,
    }[modifier]

    @guppy
    def main() -> int:
        target = qubit()
        control_qubit = qubit()
        x(control_qubit)
        # Erase the function item's identity so this is an indirect call. Modifier
        # analysis must reach the function body through its load edge.
        f: Function[[qubit, qubit], None] = loaded
        f(target, control_qubit)
        result = measure(target).read()
        discard(control_qubit)
        return 1 if result else 0

    # Each custom method flips the target; modifying the empty base body cannot.
    run_int_fn(main, expected=1, num_qubits=2)


@pytest.mark.parametrize("comptime_factory", [False, True])
def test_custom_modifier_in_returned_function_is_executed(comptime_factory, run_int_fn):
    """Returned functions retain custom modifiers with either kind of factory."""

    @guppy.unitary
    class custom_gate:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
            x(q)

    @guppy
    def loaded(q: qubit, c: qubit) -> None:
        with control(c):
            custom_gate(q)

    factory_decorator = guppy.comptime if comptime_factory else guppy

    @factory_decorator
    def factory() -> Function[[qubit, qubit], None]:
        return loaded

    @guppy
    def main() -> int:
        q = qubit()
        c = qubit()
        x(c)
        f = factory()
        f(q, c)
        result = measure(q).read()
        discard(c)
        return 1 if result else 0

    # Only the custom controlled implementation flips the target.
    run_int_fn(main, expected=1, num_qubits=2)


def test_custom_modifier_use_default_when_missing_implementation(run_int_fn):
    @guppy.unitary
    class controllable_gate:
        @guppy(controllable=True)
        def __call__(q: qubit) -> None:
            x(q)

    @guppy.unitary
    class daggerable_gate:
        @guppy(daggerable=True)
        def __call__(q: qubit) -> None:
            x(q)

    @guppy
    def main() -> int:
        controlled_target = qubit()
        control_qubit = qubit()
        x(control_qubit)
        with control(control_qubit):
            controllable_gate(controlled_target)

        daggered_target = qubit()
        with dagger:
            daggerable_gate(daggered_target)

        controlled_result = measure(controlled_target).read()
        daggered_result = measure(daggered_target).read()
        discard(control_qubit)
        return (1 if controlled_result else 0) + (2 if daggered_result else 0)

    run_int_fn(main, expected=3, num_qubits=3)


def test_double_daggered(run_int_fn):
    @guppy.unitary
    class custom_gate:
        @guppy(unitary=True)
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
            x(q)

        @guppy
        def ctrl_daggered[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
            pass

    @guppy(unitary=True)
    def helper(c: qubit, q: qubit) -> None:
        with control(c), dagger:
            custom_gate(q)

    @guppy
    def main() -> int:
        target = qubit()
        control_qubit = qubit()
        x(control_qubit)
        with dagger:
            helper(control_qubit, target)
        result = measure(target).read()
        discard(control_qubit)
        return 1 if result else 0

    run_int_fn(main, expected=1, num_qubits=2)


def test_two_control_counts_distinct_runtime(run_int_fn):
    @guppy.unitary
    class custom_gate:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled[n: nat](q: qubit, _controls: array[qubit, n]) -> None:
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


def test_struct_custom_modifier_impls_are_executed(run_int_fn):
    @guppy.struct(frozen=True)
    class CustomGates:
        enabled: bool

        @guppy
        def flip(self, q: qubit) -> None:
            x(q)

        @guppy.unitary
        class apply:
            @guppy
            def __call__(self, q: qubit) -> None:
                pass

            @guppy
            def daggered(self, q: qubit) -> None:
                if self.enabled:
                    self.flip(q)

            @guppy
            def controlled[n: nat](self, q: qubit, _controls: array[qubit, n]) -> None:
                if self.enabled:
                    self.flip(q)

            @guppy
            def ctrl_daggered[n: nat](
                self, q: qubit, _controls: array[qubit, n]
            ) -> None:
                if self.enabled:
                    self.flip(q)

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


def test_enum_custom_modifier_impls_are_executed(run_int_fn):
    @guppy.enum
    class CustomGates:
        Enabled = {}

        @guppy
        def flip(self, q: qubit) -> None:
            x(q)

        @guppy.unitary
        class apply:
            @guppy
            def __call__(self, q: qubit) -> None:
                pass

            @guppy
            def daggered(self, q: qubit) -> None:
                self.flip(q)

            @guppy
            def controlled[n: nat](self, q: qubit, _controls: array[qubit, n]) -> None:
                self.flip(q)

            @guppy
            def ctrl_daggered[n: nat](
                self, q: qubit, _controls: array[qubit, n]
            ) -> None:
                self.flip(q)

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


def test_custom_modifier(validate):

    @guppy.unitary
    class foo:
        @guppy
        def __call__[n: nat](q1: array[qubit, n]) -> None:
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
        def daggered[n: nat](q1: array[qubit, n]) -> None:
            ext_helper(q1[0])

        @guppy
        def controlled[n: nat, c: nat](
            q1: array[qubit, n], _controls: array[qubit, c]
        ) -> None:
            h(_controls[0])

        @guppy
        def ctrl_daggered[n: nat, c: nat](
            q1: array[qubit, n], _controls: array[qubit, c]
        ) -> None:
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


def test_custom_control_input_order(validate):
    @guppy.unitary
    class custom_gate:
        @guppy
        def __call__[k: nat](a: array[qubit, k], b: array[qubit, c]) -> None:
            pass

        @guppy
        def daggered[k: nat](a: array[qubit, k], b: array[qubit, c]) -> None:
            pass

        @guppy
        def controlled[k: nat, n: nat](
            a: array[qubit, k], b: array[qubit, c], ctrls: array[qubit, n]
        ) -> None:
            pass

        @guppy
        def ctrl_daggered[n: nat, k: nat](
            a: array[qubit, k], b: array[qubit, c], ctrls: array[qubit, n]
        ) -> None:
            pass

    @guppy
    def main(a: array[qubit, 2], b: array[qubit, 3], ctrl: qubit) -> None:
        with control(ctrl):
            custom_gate(a, b)
        with control(ctrl), dagger:
            custom_gate(a, b)

    validate(main.compile_function())


def test_custom_control_input_order_emulator(run_int_fn):
    @guppy.unitary
    class custom_gate:
        @guppy
        def __call__(targets: array[qubit, c]) -> None:
            pass

        @guppy
        def controlled[n: nat](
            targets: array[qubit, c], ctrls: array[qubit, n]
        ) -> None:
            cx(ctrls[0], targets[1])

    @guppy
    def main() -> int:
        targets = array(qubit(), qubit())
        ctrl = qubit()
        x(ctrl)
        with control(ctrl):
            custom_gate(targets)
        result0 = measure(targets.take(0)).read()
        result1 = measure(targets.take(1)).read()
        discard_array(targets)
        discard(ctrl)
        return 1 if result1 and not result0 else 0

    run_int_fn(main, expected=1, num_qubits=3)


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


def test_control_struct_field(validate):
    @guppy.struct
    class TwoQubits:
        a: qubit
        b: qubit

    @guppy
    def main() -> None:
        tq = TwoQubits(qubit(), qubit())
        with control(tq.a):
            x(tq.b)
        discard(tq.a)
        discard(tq.b)

    validate(main.compile())


def test_control_nested_struct_field(validate):
    @guppy.struct
    class Inner:
        a: qubit
        b: qubit

    @guppy.struct
    class Outer:
        inner: Inner
        c: qubit
        n: int

    @guppy
    def main(o: Outer) -> None:
        with control(o.inner.a):
            x(o.inner.b)
            x(o.c)
            rx(o.c, angle(o.n))

    validate(main.compile_function())


def test_control_struct_field_nested_modifiers(validate):
    @guppy.struct
    class ThreeQubits:
        a: qubit
        b: qubit
        c: qubit

    @guppy
    def main(tq: ThreeQubits) -> None:
        with dagger:
            with control(tq.a):
                x(tq.b)
            with control(tq.b):
                with control(tq.a):
                    x(tq.c)

    validate(main.compile_function())


def test_control_tuple_element(validate):
    @guppy
    def main() -> None:
        t = (qubit(), qubit())
        with control(t[0]):
            x(t[1])
        discard(t[0])
        discard(t[1])

    validate(main.compile())


def test_control_nested_tuple_element(validate):
    @guppy
    def main(t: tuple[tuple[qubit, qubit], qubit]) -> None:
        with control(t[0][0]):
            x(t[0][1])
            x(t[1])

    validate(main.compile_function())


def test_control_tuple_in_struct(validate):
    @guppy.struct
    class Pair:
        qs: tuple[qubit, qubit]
        c: qubit

    @guppy
    def main(p: Pair) -> None:
        with control(p.qs[0]):
            x(p.qs[1])
            x(p.c)

    validate(main.compile_function())


def test_control_struct_field_nested_function(validate, use_experimental_features):
    @guppy.struct(frozen=True)
    class Params:
        a: int
        b: int

    @guppy
    def main() -> None:
        p = Params(1, 2)
        c = qubit()
        t = qubit()
        with control(c):
            # The nested function captures `p` as a whole, so the field access
            # `p.b` outside of it must not be captured separately.
            def inner() -> int:
                return p.a

            _ = inner() + p.b
            x(t)
        discard(c)
        discard(t)

    validate(main.compile_function())


def test_control_struct_field_assigned_in_body(validate):
    @guppy.struct
    class Params:
        a: int
        b: int

    @guppy
    def main() -> None:
        p = Params(1, 2)
        c = qubit()
        t = qubit()
        with control(c):
            # Assigning to a field requires capturing the whole struct
            p.a = 3
            _ = p.b
            x(t)
        discard(c)
        discard(t)

    validate(main.compile_function())


def test_control_struct_field_dynamic_subscript(validate):
    @guppy.struct
    class Register:
        qs: array[qubit, 3]
        i: int

    @guppy
    def main(r: Register) -> None:
        c = qubit()
        with control(c):
            x(r.qs[r.i])
        discard(c)

    validate(main.compile_function())


def test_control_struct_field_in_branch(validate):
    @guppy.struct
    class Params:
        a: int
        b: int

    @guppy
    def main(p: Params) -> None:
        c = qubit()
        t = qubit()
        with control(c):
            if p.a > p.b:
                x(t)
        discard(c)
        discard(t)

    validate(main.compile_function())


def test_control_struct_field_method_call(validate):
    @guppy.struct
    class Data:
        xs: array[int, 3]

    @guppy
    def main(d: Data) -> None:
        c = qubit()
        t = qubit()
        with control(c):
            # `d.xs.copy` is a method, not a field, so only `d.xs` is captured
            _ = d.xs.copy()
            x(t)
        discard(c)
        discard(t)

    validate(main.compile_function())


def test_dagger_unmixed_uses_of_mixed(validate):
    @guppy.struct
    class Qubits:
        q1: qubit
        q2: qubit

    @guppy.struct
    class Mixed:
        q: qubit
        a: angle

    @guppy.struct
    class Outer:
        qs: Qubits
        m: Mixed
        a: angle

    @guppy.struct
    class Params:
        a: angle
        b: angle

    @guppy(daggerable=True)
    def use_qubits(s: Qubits) -> None:
        h(s.q1)

    @guppy(daggerable=True)
    def use_pair(t: tuple[qubit, qubit]) -> None:
        h(t[0])

    @guppy(daggerable=True)
    def main(
        s: Outer,
        t: tuple[tuple[qubit, qubit], tuple[qubit, angle], angle],
        qs: array[Qubits, 2],
        ps: array[Params, 2],
        i: int,
    ) -> None:
        # Unmixed projections of mixed values can be used as a whole
        use_qubits(s.qs)
        use_pair(t[0])
        # Static projections through mixed intermediates only use the leaf wires
        rx(s.m.q, s.m.a)
        rx(t[1][0], t[1][1])
        rx(s.qs.q2, s.a)
        rx(t[0][1], t[2])
        # Subscripts into arrays of unmixed values are fine, including assignment
        h(qs[i].q1)
        rx(qs[i].q2, ps[i].a)
        ps[i].b = ps[i].a

    validate(main.compile_function())


def test_custom_modifier_accepts_docstring(validate) -> None:
    """guppy.unitary classes accept docstrings."""

    @guppy.unitary
    class custom_modified:
        """Docstring here"""

        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def daggered(q: qubit) -> None:
            pass

    @guppy
    def main() -> None:
        q = qubit()
        with dagger:
            custom_modified(q)
        discard(q)

    validate(main.compile())


def test_signed_division_in_dagger(validate) -> None:
    @guppy
    def main(x: int, y: int) -> int:
        q = qubit()
        with dagger:
            z = x // y
            rz(q, angle(float(z % 4)))
        discard(q)
        return 1

    validate(main.compile_function())


def test_control_index_not_checked_with_inner_dagger(validate):
    @guppy
    def nested(cs: array[qubit, 2], q: qubit) -> None:
        with control(cs[int(measure(qubit()).read())]):
            with dagger:
                h(q)

    validate(nested.compile_function())


def test_control_index_not_checked_with_same_block_dagger(validate):
    @guppy
    def nested(cs: array[qubit, 2], q: qubit) -> None:
        with dagger, control(cs[int(measure(qubit()).read())]):
            h(q)

    validate(nested.compile_function())
