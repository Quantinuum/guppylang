from guppylang import guppy
from guppylang.std.builtins import array, qubit, comptime
from guppylang.std.quantum import discard_array
from typing import Generic

n_qubits = guppy.nat_var("n_qubits")

@guppy.struct
class Register(Generic[n_qubits]):
    register: array[qubit, n_qubits]

    @guppy
    def anything(self) -> bool:
        return True

@guppy
def my_foo(main_register: Register[4]) -> None:
    register = main_register.register
    if main_register.anything():
       pass

b = 4

@guppy
def main() -> None:
    qs = array(qubit() for _ in range(comptime(b)))
    reg = Register(qs)
    my_foo(reg)
    qs = reg.register
    discard_array(qs)

main.check()