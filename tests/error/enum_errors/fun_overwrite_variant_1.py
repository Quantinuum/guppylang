from guppylang.decorator import guppy


@guppy.enum
class MyEnum:
    name = {"x": int}

    @guppy
    def name(self) -> str:
        return "name"


MyEnum.compile()
