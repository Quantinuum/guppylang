from guppylang.decorator import guppy


@guppy.enum
class MyEnum:

    @guppy
    def name(self) -> str:
        return "name"

    name = {"x": int}


MyEnum.compile()
