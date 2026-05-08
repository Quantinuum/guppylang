from guppylang import guppy, qubit


@guppy(dagger=True)
def test() -> None:
    p = qubit()


test.compile()
