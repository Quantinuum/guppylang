import pytest


def test_removed_quantum_functional():
    """Asserts that the module breaker works as intended to break tket imports."""

    with pytest.raises(
        ImportError,
        match="`guppylang.std.quantum_functional` has been removed. Import from `guppylang.std.quantum_functional` instead.",  # noqa: E501, RUF043
    ):
        import guppylang.std.quantum_functional  # noqa: F401
