from guppylang import guppy, qubit


@guppy.declare
def foo(x: qubit) -> None: ...


@guppy.comptime(power=True)
def test(x: qubit) -> None:
    foo(x)


test.compile_function()
