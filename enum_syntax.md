
from guppylang.std.quantum import qubit

@guppy.enum
class MyEnum:
    Variant1 = {"a": int, "b": qubit}
    Variant2 = {}
    Variant3 = (int, float)



Strating from a Rust example:
```rust
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
```


In guupy syntax (assuming anonymous variants) we will have:

```python
@guppy.enum
class Message:
    Quit = {}
    Resize = { width: int, height: int}
    Move = {x: int, y: int}
    Echo = (str)
    ChangeColor = (int, int, int)
```
We need to decide a way to represent in python syntax this:
```rust
    Message::Resize {
        width: 10,
        height: 30,
    },
    Message::Move { x: 10, y: 15 },
    Message::Echo(String::from("hello world")),
    Message::ChangeColor(200, 255, 255),
    Message::Quit,
```

Using a class methods,like `variant = Message.resize(2,3)` ?
