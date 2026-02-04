from guppylang.decorator import guppy


def build():
    @guppy.struct
    class Foo:
        x: "blah"

    return Foo


build().compile() # type: ignore