from guppylang import guppy

@guppy
def foo[T: (Copy, Bogus, Drop)](t: T) -> T:
    return t

@guppy
def main() -> None:
    foo(42)

main.check()
