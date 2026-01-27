from guppylang.decorator import guppy
from guppylang.std.builtins import array

@guppy
def main() -> int:
      matrix = array(array(i + j for i in range(10)) for j in range(5))
      return matrix[5][0] 

main.compile()