from guppylang.decorator import guppy


@guppy.enum
class MyEnum:

    @guppy.unitary
    class name:
        @guppy
        def __call__(self) -> None:
            pass

    name = {"x": int}


MyEnum.compile()
