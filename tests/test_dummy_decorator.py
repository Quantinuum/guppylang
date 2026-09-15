from guppylang_internals.dummy_decorator import _dummy_custom_decorator


def test_dummy_custom_decorator_supports_factories():
    @_dummy_custom_decorator("example.name")
    def example() -> None:
        pass

    assert example.__name__ == "example"
