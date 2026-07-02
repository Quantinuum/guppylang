from guppylang import qubit
from guppylang.decorator import guppy


@guppy
def main[Q: qubit]() -> None:
    pass


main.compile()
