from guppylang import guppy
from guppylang.std.builtins import Function, Daggerable
from guppylang.std.quantum import qubit

@guppy(unitary=True)
def unitary_fun(q: qubit) -> None:
    pass


@guppy
def apply_plain(f: Function[[qubit], None], q: qubit) -> None:
    f(q)


@guppy
def take_daggerable_consumer(
    consumer: Function[[Daggerable[[qubit], None], qubit], None], q: qubit
) -> None:
    consumer(unitary_fun, q)


@guppy
def main(q: qubit) -> None:
    # The Daggerable constraint is scoped to `take_daggerable_consumer`, so it's not
    # contravariant w.r.t. to the Function that is passed in!
    take_daggerable_consumer(apply_plain, q)


main.compile_function()
