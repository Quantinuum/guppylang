from guppylang import guppy, qubit


@guppy.declare(unitary=True)
def uni_discard(q: qubit) -> None: ...


@guppy.comptime(dagger=True)
def test() -> None:
    q = qubit()
    uni_discard(q)


test.compile_function()
