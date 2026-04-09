from guppylang import guppy


@guppy.declare(link_name="lib1.my_super_adder")
def super_adder(x: int) -> int: ...
