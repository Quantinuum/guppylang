from guppylang import guppy, qubit


@guppy.declare(power=True)
def foo(x: qubit) -> None: ...


@guppy.comptime(unitary=True)
def test(x: qubit) -> None:
    foo(x)


test.compile_function()
