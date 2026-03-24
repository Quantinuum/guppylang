from guppylang.decorator import guppy


@guppy.enum
class MyEnum:
    var1 = {"x": int}

    def nonguppy_method(self) -> None:
        pass


MyEnum.compile()
