from guppylang.decorator import guppy


def test_docstring(validate):
    @guppy
    def f() -> None:
        "Example docstring"

    @guppy
    def g() -> None:
        """Multi
        line
        doc
        string.
        """
        f()

    @guppy
    def nested() -> None:
        """Test docstrings in nested functions"""

        def f_nested() -> None:
            "Example docstring"
            f_nested()
            g()

        def g_nested() -> None:
            """Multi
            line
            doc
            string.
            """

    validate(f.compile_function())
    validate(g.compile_function())
    validate(nested.compile_function())
