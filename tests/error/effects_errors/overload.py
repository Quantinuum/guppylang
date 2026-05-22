from guppylang.decorator import guppy

T = guppy.type_var("T")

@guppy.declare
def variant1(x : T) -> T: ...

@guppy.declare(max_effects=[])
def variant2(x : int) -> int: ...

@guppy.overload(variant1, variant2)
def only_pure_for_int(): ...

@guppy(max_effects=[])
def pure_func(x: int) -> int:
    return only_pure_for_int(x + 1)

@guppy
def impure_func(x: float) -> float:
    return only_pure_for_int(x + 1.0)

@guppy(max_effects=[])
def bad_pure_func(x: float) -> float:
    return only_pure_for_int(x)

@guppy
def main() -> None:
    pure_func(5)
    impure_func(5.0)
    bad_pure_func(3.14)

main.compile()