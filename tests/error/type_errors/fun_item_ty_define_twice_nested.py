from tests.util import compile_guppy


@compile_guppy
def main(b: bool) -> None:
    if b:
        def foo() -> None:
            pass
    else:
        def foo() -> None:
            pass
    foo()

