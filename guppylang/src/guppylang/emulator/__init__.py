"""
Emulation of Guppy programs powered by the selene-sim package.

Provides a configurable interface for compiling Guppy functions
into an emulator instance, and a configurable builder for setting
instance options and executing.

Emulation returns :py:class:`EmulatorResult` objects, which contain the result output
by the emulation. Results are recorded by calling ``result("tag", value)`` in the
Guppy program, and can include both quantum measurement outcomes and classical
outputs.


Basic emulation
-----------------

Calling ``.emulator`` on a Guppy function compiles it into an
:py:class:`EmulatorInstance`. The method has a required parameter
for the number of qubits to allocate. This cannot be
inferred from the program automatically as it can request an arbitrary number of qubits
at runtime.

Calling ``.run()`` on the instance runs the emulation, returning an
:py:class:`EmulatorResult` object containing the results.

.. code-block:: python

    from guppylang import guppy
    from guppylang.std.builtins import result
    from guppylang.std.quantum import qubit, measure

    @guppy
    def foo() -> None:
        q = qubit()
        result("q", measure(q))

    foo.emulator(n_qubits=1).run()

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

    foo.emulator(1).with_error_model(DepolarizingErrorModel()).run()

State results
-----------------

Calling ``state_result("tag", q1, q2)`` in the Guppy program will record the
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

.. code-block:: ipython

    from guppylang import guppy
    from guppylang.std.debug import state_result
    from guppylang.std.quantum import qubit, measure, cx, h

    @guppy
    def foo() -> None:
        # Measure one qubit in a bell state
        q0 = qubit()
        h(q0)
        q1 = qubit()
        cx(q0, q1)
        state_result("q0", q0)
        measure(q0)
        measure(q1)

    res = foo.emulator(2).run()
    # get state outputs at shot 0, tag "q0"
    res.partial_state_dicts()[0]["q0"].state_distribution()

Output is a uniform distribution over the two basis states of the qubit:

.. code-block:: python

    [TracedState(probability=0.5, state=array([1.+0.j, 0.+0.j])),
    TracedState(probability=0.5, state=array([0.+0.j, 1.+0.j]))]
"""

from .builder import EmulatorBuilder
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
    "QsysShot",
    "StateVector",
    "TaggedResult",
    "TracedState",
]
