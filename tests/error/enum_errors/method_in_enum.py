from guppylang.decorator import guppy


@guppy.enum
class MyEnum:
    v1 = {"x": int}

    @guppy
    def method(self):
        pass


MyEnum.compile()
