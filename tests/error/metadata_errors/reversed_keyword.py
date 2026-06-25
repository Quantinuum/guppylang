from guppylang import guppy
from guppylang.decorator import metadata


@guppy
@metadata("tket.unitary", "value1")
def main() -> None:...
    # """Main function for the GuppyLang program."""
    # pass

main.compile()