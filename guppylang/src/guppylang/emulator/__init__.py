"""
Emulation of Guppy programs powered by the selene-sim package.

Provides a configurable interface for compiling Guppy functions
into an emulator instance, and a configurable builder for setting
instance options and executing.

Emulation returns :py:class:`EmulatorResult` objects, which contain the result output
by the emulation. Results are recorded by calling ``output("tag", value)`` in the
Guppy program, and can include both quantum measurement outcomes and classical
outputs.


Basic emulation
-----------------

Calling ``.emulator()`` on a Guppy function compiles it into an
:py:class:`EmulatorInstance`. The method has a required parameter
for the number of qubits to allocate. This cannot be inferred from the program
fully automatically as it can request an arbitrary number of qubits at runtime.

Calling ``.run()`` on the instance runs the emulation, returning an
:py:class:`EmulatorResult` object containing the results.

.. code-block:: python

    from guppylang import guppy
    from guppylang.std.builtins import output
    from guppylang.std.quantum import qubit, measure

    @guppy
    def foo() -> None:
        q = qubit()
        output("q", measure(q).read())

    foo.emulator(n_qubits=1).run()

.. hint::

    You can omit ``n_qubits`` from the ``.emulator()`` call if you add the
    ``@expected_qubits`` decorator to ``foo``:

    .. code-block:: python

        from guppylang.decorator import expected_qubits

        @guppy
        @expected_qubits(1)
        def foo() -> None:
            pass # ...

        foo.emulator().run()

Change simulation method
--------------------------

The default simulation method is statevector simulation, powered
by the Quest selene plugin.
The simulation method can be changed by calling methods on the
:py:class:`EmulatorBuilder` instance that return updated instances.
For example to use the stabilizer simulator with clifford circuits:

.. code-block:: python

    foo.emulator(1).stabilizer_sim().run()

See also :py:meth:`EmulatorInstance.coinflip_sim` for a no-quantum simulation.

In addition arbitrary selene-sim ``Simulator`` plugins can be used
by calling :py:meth:`EmulatorInstance.with_simulator`.


Configuring emulator instances
-------------------------------

In general the emulation can be configured by chaining ``with_*`` methods on the
:py:class:`EmulatorInstance` object. Each method returns a new instance with the
updated configuration.

For example, the default number of shots run is 1, to change that:

.. code-block:: python

    foo.emulator(n_qubits=1).with_shots(1000).run()

Or update many options at once:

.. code-block:: python

    foo.emulator(n_qubits=1).with_shots(1000).with_seed(42).with_shot_offset(10).run()

See the :py:class:`EmulatorInstance` documentation for a full list of options and their
defaults.


Noisy simulation
-----------------

Selene-sim supports noisy simulation, which can be enabled by setting an error model
on the emulator instance.

.. code-block:: python

    from selene_sim.backends.bundled_error_models import DepolarizingErrorModel

    error_model = DepolarizingErrorModel(
        random_seed=123141,
        p_1q=1e-5,
        p_2q=1.4e-4,
        p_meas=1e-3,
        p_init=1e-5
    )

    foo.emulator(1).with_error_model(error_model).run()

State results
-----------------

Calling ``state_output("tag", q1, q2)`` in the Guppy program will record the
state of the qubits `q1` and `q2` in the outputs.
The particular representation of the state depends on the simulation backend,
the default statevector simulator returns a :py:class:`StateVector` object
which is just a numpy array of complex amplitudes.

In general the qubits you request state for may not be all the qubits in the fully
entangled state, in which case the remaining qubits are traced over and a
probabilistic distribution over statws is returned.

The two methods :py:meth:`EmulatorResult.partial_states` and
:meth:`EmulatorResult.partial_state_dicts` extract state results
from the emulator output as :py:class:`PartialVector` objects.

.. code-block:: python

    from guppylang import guppy
    from guppylang.std.debug import state_output
    from guppylang.std.quantum import qubit, measure, cx, h

    @guppy
    def foo() -> None:
        # Measure one qubit in a bell state
        q0 = qubit()
        h(q0)
        q1 = qubit()
        cx(q0, q1)
        state_output("q0", q0)
        measure(q0)
        measure(q1)

    res = foo.emulator(2).run()
    # get state outputs at shot 0, tag "q0"
    res.partial_state_dicts()[0]["q0"].state_distribution()

Output is a uniform distribution over the two basis states of the qubit:

.. code-block:: python

    [TracedState(probability=0.5, state=array([1.+0.j, 0.+0.j])),
    TracedState(probability=0.5, state=array([0.+0.j, 1.+0.j]))]



Emulator Entrypoint Arguments
-----------------------------

Guppy functions taking parameters of certain types can be called with arguments when
emulating. The following types are supported: `int`, `float`, `bool`, and `array` of
these types.

The main benefit of this approach as opposed to hardcoding values in the function or
using python value capture is that the program is compiled once, meaning large parameter
sweeps can be done without recompiling the program each time - often significantly
improving performance. Emulations of variational algorithms in particular can
benefit from this.

Bind parameter values using keyword arguments to :py:meth:`EmulatorInstance.run`:

.. code-block:: python

    from guppylang import guppy
    from guppylang.std.array import array

    @guppy
    def entry_args(theta: float, k: array[int, 1]) -> None:
        output("doubled", theta * 2.0)
        output("k1", k[0] + 1)


    entry_args.emulator(n_qubits=1).run(theta=1.5, k=[3])

.. code-block:: python
    # output
    EmulatorResult(results=[QsysShot(entries=[('doubled', 3.0), ('k1', 4)])])

Given Guppy emulation is also faster over shots than multiple separate `run` calls,
parameter sweeps over shots are also supported via the
:py:meth:`EmulatorInstance.run_per_shot` method, which takes a sequence of argument
mappings to run the program with for each shot:

.. code-block:: python

    entry_args.emulator(n_qubits=1).run_per_shot([
        {"theta": 1.5, "k": [3]},
        {"theta": 2.0, "k": [4]}
    ])

.. code-block:: python
    # output
    EmulatorResult(results=[
        QsysShot(entries=[('doubled', 3.0), ('k1', 4)]),
        QsysShot(entries=[('doubled', 4.0), ('k1', 5)])
    ])

The number of shots is inferred from the length of the argument sequence, if it
conflicts with the value set with :py:meth:`EmulatorInstance.with_shots` an error is
raised.


Target Quantinuum Platform
--------------------------

By default the emulator compiler targets the Quantinuum Helios platform. By specifying
the `platform` keyword argument to :py:meth:`GuppyCompilableProgram.emulator`
you can target other Quantinuum platforms, which may have different gate sets and
native gate decompositions, for example to target the upcoming Sol platform:

.. code-block:: python

    foo.emulator(n_qubits=1, platform="sol").run()

When submitting to hardware through Nexus the target platform is automatically
inferred from the Nexus backend, so this option is only relevant for local emulation.

This compilation target is also independent of the platform-specific standard libraries,
like `guppylang.std.qsystem.helios` or `guppylang.std.qsystem.sol`, which can be used to
program using platform-specific gates and features. The compiler supports automatic
retargeting of these gates to the specified platform. So to run platform-specific
code with the same compilation target, make sure the `platform` argument matches the
standard library used:

.. code-block:: python
    from guppylang.std.qsystem.sol import phased_xx
    from guppylang.std.angles import pi

    @guppy
    def foo() -> None:
        q0 = qubit()
        q1 = qubit()
        # use Sol primitive gates
        phased_xx(q0, q1, pi, pi)
        measure(q0)
        measure(q1)

    # run on Sol platform
    foo.emulator(n_qubits=2, platform="sol").run()
"""

from .builder import EmulatorBuilder, Platform
from .exceptions import EmulatorError
from .instance import EmulatorInstance
from .result import EmulatorResult, QsysShot, TaggedResult
from .state import PartialState, PartialVector, StateVector, TracedState

__all__ = [
    "EmulatorBuilder",
    "EmulatorError",
    "EmulatorInstance",
    "EmulatorResult",
    "PartialState",
    "PartialVector",
    "Platform",
    "QsysShot",
    "StateVector",
    "TaggedResult",
    "TracedState",
]
