from guppylang.decorator import expected_qubits, guppy


@guppy.unitary
class Foo:
    @guppy
    def __call__() -> None:
        pass

    @guppy
    @expected_qubits(2)
    def controlled() -> None:
        pass
