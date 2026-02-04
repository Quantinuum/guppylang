from guppylang.decorator import guppy


@guppy
def main() -> None:
    l = [1, 2, 3]
    l[0] = 3

main.compile()