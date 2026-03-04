from guppylang import guppy

@guppy.struct
class Point:
    x: int
    y: int

@guppy
def main(p: Point, x: int) -> None:
    match p:
        case Point(1,3,4):
            z = 66

main.check()

# TODO: NICOLA do the same for enums
