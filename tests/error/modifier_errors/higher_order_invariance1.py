from guppylang import guppy
from guppylang.std.builtins import Function, Daggerable
from guppylang.std.quantum import qubit

@guppy(controllable=True)
def control_fun(q: qubit) -> None:
    pass


@guppy(daggerable=True)
def apply_dagger(f: Daggerable[[qubit], None], q: qubit) -> None:
    f(q)


@guppy
def take_plain_consumer(
    consumer: Function[[Function[[qubit], None], qubit], None], q: qubit
) -> None:
    consumer(control_fun, q)


@guppy
def main(q: qubit) -> None:
    # consumer must accept any function, but `apply_dagger` only accepts daggerable
    take_plain_consumer(apply_dagger, q)


main.compile_function()
