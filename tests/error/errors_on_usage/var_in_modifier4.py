import guppylang
from guppylang import guppy
from guppylang.std.builtins import dagger
guppylang.enable_experimental_features()

@guppy
def main() -> None:
    with dagger:
        i = 3
    u = i
                
main.check()