from guppylang.decorator import guppy
from guppylang.std.builtins import array

T = guppy.type_var("T")

@guppy.declare
def foo() -> T: ...

@guppy
def main() -> None:
   array(foo())

main.compile()
