from guppylang import guppy
from guppylang.std.builtins import power

@guppy
def main() -> None:
    with power(3):
        i = 3
    u = i
                
main.check()
