
from guppylang import guppy

from tests.util import compile_guppy


@guppy.enum
class Message:  # noqa: F811
    Quit = {"x": int}  # noqa: RUF012


@compile_guppy
def use_enum() -> None:
    variant = Message.Quit(1)
    variant.x


