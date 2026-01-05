from guppylang.decorator import guppy

X = guppy.type_var("X")


class Generic:
    """Fake Generic type that doesn't check for type var uniqueness."""

    def __class_getitem__(cls, item):
        return cls


@guppy.enum
class MyEnum(Generic[X, X]):
    var = {"x": int}


MyEnum.compile()
