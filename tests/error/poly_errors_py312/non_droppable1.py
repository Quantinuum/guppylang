from hugr import tys
from guppylang import guppy
from guppylang_internals.decorator import custom_type


@custom_type(tys.Tuple(), droppable=False)
class NonDroppable:
    pass


@guppy
def main[D: NonDroppable]() -> None:
    pass


main.compile()
