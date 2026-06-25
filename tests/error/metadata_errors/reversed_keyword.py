from guppylang import guppy
from guppylang.decorator import metadata


@guppy
@metadata("tket.unitary", "value1")
def main() -> None:
    pass

