from guppylang import guppy, array


def test_import_func(validate):
    from tests.integration.modules.mod_a import f, g

    @guppy
    def test(x: int) -> int:
        return f(x) + g()

    validate(test.compile_function())


def test_import_type(validate):
    from tests.integration.modules.mod_a import MyType

    @guppy
    def test(x: MyType) -> MyType:
        # Check that we've correctly imported the __neg__ method
        return -x

    validate(test.compile_function())


def test_func_alias(validate):
    from tests.integration.modules.mod_a import f as g

    @guppy
    def test(x: int) -> int:
        return g(x)

    validate(test.compile_function())


def test_type_alias(validate):
    from tests.integration.modules.mod_a import MyType as MyType_Alias  # noqa: TC001

    @guppy
    def test(x: "MyType_Alias") -> "MyType_Alias":
        # Check that we still have the __neg__ method
        return -x

    validate(test.compile_function())


def test_type_transitive(validate):
    # `g` returns a type that was defined in `mod_a`
    from tests.integration.modules.mod_c import g

    @guppy
    def test() -> int:
        x = g()  # Type of x was defined in `mod_a`
        return int(-x)  # Call method that was defined in `mod_a`

    validate(test.compile_function())


def test_type_transitive_conflict(validate):
    from tests.integration.modules.mod_b import MyType
    from tests.integration.modules.mod_c import g

    @guppy
    def test(ty_b: MyType) -> MyType:
        ty_a = g()  # g returns a type with the same name `MyType`
        return +ty_b

    validate(test.compile_function())


def test_func_transitive(validate):
    # `h` calls a function that was defined in `mod_a`
    from tests.integration.modules.mod_c import h

    @guppy
    def test(x: int) -> int:
        return h(x)

    validate(test.compile_function())


def test_qualified(validate):
    import tests.integration.modules.mod_a as mod_a
    import tests.integration.modules.mod_b as mod_b

    @guppy
    def test(x: int, y: bool) -> tuple[int, bool]:
        return mod_a.f(x), mod_b.f(y)

    validate(test.compile_function())


def test_qualified_types(validate):
    import tests.integration.modules.mod_a as mod_a
    import tests.integration.modules.mod_b as mod_b

    @guppy
    def test(x: mod_a.MyType, y: mod_b.MyType) -> tuple[mod_a.MyType, mod_b.MyType]:
        return -x, +y

    validate(test.compile_function())


def test_nat_var_alias(validate):
    from tests.integration.modules.mod_a import n as nat_var

    @guppy
    def test(arr: array[int, nat_var]) -> int:
        return arr[0]

    validate(test.compile_function())
