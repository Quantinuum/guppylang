from typing import Generic
from tests.util import compile_guppy
from guppylang import guppy


T = guppy.type_var("T")

@guppy.enum
class Enum(Generic[T]):              # pyright: ignore[reportInvalidTypeForm]
    Var = {"value": T}                      # pyright: ignore[reportInvalidTypeForm]

@compile_guppy
def main(d: Enum[T]) -> None:         # pyright: ignore[reportInvalidTypeForm]
    match d:
        case Enum.Var(1):
            pass

