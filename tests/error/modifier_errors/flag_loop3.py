from guppylang.decorator import guppy


@guppy(dagger=True, power=True)
def test(i: int) -> None:
    x = (n**2 for n in [1,2] if n>5 if n<10)


test.compile()
