from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit, measure, discard_array

@guppy
def main() -> None:
   qs = array(qubit() for _ in range(5))
   q = qs.take(0)
   measure(q)
   qs.put(qubit(), 10)  # Out of bounds
   discard_array(qs)

main.compile()



