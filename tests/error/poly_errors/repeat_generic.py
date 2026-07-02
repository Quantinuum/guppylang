from guppylang.decorator import guppy


class Generic:
    """Mock of the `typing.Generic` class to allow us to inherit from `Generic` multiple
    times.
    """

    def __class_getitem__(cls, item):
        return cls


T = guppy.type_var("T")


@guppy.struct
class MyStruct[S](Generic[T]):
    pass


MyStruct.check()
