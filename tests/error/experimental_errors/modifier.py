from guppylang.decorator import guppy


@guppy
def main() -> None:
    with dagger:
        pass


main.compile_function()
