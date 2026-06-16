from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit, measure, h, discard_array

@guppy
def main() -> None:
   qs = array(qubit() for _ in range(5))
   qs.take(10)
   discard_array(qs)

main.compile()