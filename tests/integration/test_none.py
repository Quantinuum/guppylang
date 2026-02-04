from guppylang.decorator import guppy


def test_none(validate, run_int_fn):
    @guppy
    def foo() -> None:
        return None

    @guppy
    def bar(x: None, y: int) -> int:
        return y

    @guppy
    def main() -> int:
        return bar(foo(), 42)

    validate(main.compile_function())
    run_int_fn(main, expected=42)
