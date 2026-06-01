from guppylang.decorator import guppy
from guppylang.std.builtins import result

@guppy(effects=[])
def main() -> int:
   result("foo", True)
   return 3

main.compile_function()