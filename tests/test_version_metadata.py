import guppylang
import guppylang_internals
from guppylang import guppy
from hugr.metadata import HugrGenerator, HugrUsedExtensions
from semver import Version


def test_metadata():
    @guppy
    def foo() -> None:
        pass

    hugr = foo.compile().modules[0]
    meta = hugr.module_root.metadata
    assert (
        meta[HugrGenerator].name
        == f"guppylang (guppylang-internals-v{guppylang_internals.__version__})"
    )
    assert meta[HugrGenerator].version == Version.parse(guppylang.__version__)

    used = meta[HugrUsedExtensions]
    assert len(used) == 0, "Expected no used extensions for a simple function"


def test_used_extensions_computed_dynamically():
    """Test that used extensions are computed based on actual usage."""
    from guppylang.std.builtins import owned
    from guppylang.std.quantum import h, qubit

    # A simple function with no special ops should only have minimal extensions
    @guppy
    def simple() -> None:
        pass

    simple_pkg = simple.compile()
    simple_ext_names = {e.name for e in simple_pkg.extensions}

    # A function using quantum ops should include quantum-related extensions
    @guppy
    def quantum_func(q: qubit @ owned) -> qubit:
        h(q)
        return q

    quantum_pkg = quantum_func.compile_function()
    quantum_ext_names = {e.name for e in quantum_pkg.extensions}

    # Quantum function should have more extensions than the simple function
    assert len(quantum_ext_names) > len(simple_ext_names)

    # Quantum function should include the tket.quantum extension
    assert "tket.quantum" in quantum_ext_names

    # Simple function should not include quantum extensions
    assert "tket.quantum" not in simple_ext_names
