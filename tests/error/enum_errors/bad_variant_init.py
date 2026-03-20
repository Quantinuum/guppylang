from guppylang import guppy

@guppy.enum
class Message:
    Quit = {}  # noqa: RUF012

@guppy
def main() -> None:
    msg1 = Message.BadVariant() 
 
main.compile_function()
