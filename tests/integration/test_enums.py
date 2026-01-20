import pytest

from guppylang import guppy
from tests.util import compile_guppy


# TODO: NICOLA temporary test, to be substituted with `test_basic_enum`
# when enum implementation is complete
def test_enum_syntax():
    @guppy.enum
    class EmptyEnum:
        pass

    @guppy.enum
    class GenericEnum:
        VariantA = {}
        VariantB = {"x": int, "y": float}

        @guppy
        def describe(variant: "GenericEnum") -> int:
            return 42

    EmptyEnum.compile()
    GenericEnum.compile()


@pytest.mark.skip
def test_basic_enum():
    """
    Stating from a Rust example:
    rust
    enum Message {
        Quit,
        Resize { width: i32, height: i32},
        Move {x: u64, y: u64},
        Echo(String),
        ChangeColor(i32, i32, i32),
    }

    fn main() {
        let messages: [Message; 5] = [
            Message::Resize {
                width: 10,
                height: 30,
            },
            Message::Move { x: 10, y: 15 },
            Message::Echo(String::from("hello world")),
            Message::ChangeColor(200, 255, 255),
            Message::Quit,
        ];

    }
    """

    @guppy.enum
    class Message:
        Quit = {}  # noqa: RUF012
        Resize = {"width": int, "height": int}  # noqa: RUF012
        Move = {"x": int, "y": int}  # noqa: RUF012
        Echo = str
        ChangeColor = (int, int, int)

    @compile_guppy
    def use_enum() -> None:
        variant1 = Message.Resize(2, 3)
        variant2 = Message.Echo("hello world")
        variant3 = Message.Quit()
        variant4 = Message.ChangeColor(200, 255, 255)
