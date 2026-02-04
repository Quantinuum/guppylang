from guppylang.decorator import guppy


@guppy.struct
class StructA:
    x: "list[StructB]"


@guppy.struct
class StructB:
    y: "StructA"


StructB.compile()
