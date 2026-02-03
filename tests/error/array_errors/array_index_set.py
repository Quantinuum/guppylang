from guppylang.decorator import guppy
from guppylang.std.builtins import array

@guppy
def main() -> None:
      arr = array(0 for _ in range(5))
      arr[10] = 42

main.compile()