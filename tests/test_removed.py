import pytest


def test_removed_quantum_functional():
    with pytest.raises(
        ImportError,
        match=r"`guppylang.std.quantum_functional` has been removed. Import from `guppylang.std.quantum_functional` instead.",  # noqa: E501
    ):
        import guppylang.std.quantum_functional  # noqa: F401


def test_removed_mem_swap():
    from guppylang.std.builtins import mem_swap

    with pytest.raises(
        ImportError,
        match=r"The function `mem_swap` has been moved to `guppylang.std.mem`, and can no longer be imported from `guppylang.std.builtins`.",  # noqa: E501
    ):
        mem_swap(1, 2)


def test_removed_bytecast_float_to_nat():
    from guppylang.std.builtins import bytecast_float_to_nat

    with pytest.raises(
        ImportError,
        match=r"The function `bytecast_float_to_nat` has been moved to `guppylang.std.num`, and can no longer be imported from `guppylang.std.builtins`.",  # noqa: E501
    ):
        bytecast_float_to_nat(1.0)


def test_removed_bytecast_nat_to_float():
    from guppylang.std.builtins import bytecast_nat_to_float

    with pytest.raises(
        ImportError,
        match=r"The function `bytecast_nat_to_float` has been moved to `guppylang.std.num`, and can no longer be imported from `guppylang.std.builtins`.",  # noqa: E501
    ):
        bytecast_nat_to_float(1)


def test_removed_barrier():
    from guppylang.std.builtins import barrier

    with pytest.raises(
        ImportError,
        match=r"The function `barrier` has been moved to `guppylang.std.platform`, and can no longer be imported from `guppylang.std.builtins`.",  # noqa: E501
    ):
        barrier()


def test_removed_Range():
    from guppylang.std.builtins import Range

    with pytest.raises(
        ImportError,
        match=r"The class `Range` has been moved to `guppylang.std.iter`, and can no longer be imported from `guppylang.std.builtins`.",  # noqa: E501
    ):
        Range()


def test_removed_SizedIter():
    from guppylang.std.builtins import SizedIter

    with pytest.raises(
        ImportError,
        match=r"The class `SizedIter` has been moved to `guppylang.std.iter`, and can no longer be imported from `guppylang.std.builtins`.",  # noqa: E501
    ):
        SizedIter()


def test_removed_ArrayIter():
    from guppylang.std.builtins import ArrayIter

    with pytest.raises(
        ImportError,
        match=r"The class `ArrayIter` has been moved to `guppylang.std.array`, and can no longer be imported from `guppylang.std.builtins`.",  # noqa: E501
    ):
        ArrayIter()


def test_removed_FrozenArrayIter():
    from guppylang.std.builtins import FrozenarrayIter

    with pytest.raises(
        ImportError,
        match=r"The class `FrozenarrayIter` has been moved to `guppylang.std.array`, and can no longer be imported from `guppylang.std.builtins`.",  # noqa: E501
    ):
        FrozenarrayIter()
