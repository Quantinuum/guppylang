from tests.util import compile_guppy

@compile_guppy
def complex_control_flow(a: int, b: int, c: bool) -> int:
    if a > 10:
        if b < 5:
            y = a + b
        else:
            if c:
                return 10
            else:
                x = a - b
    else:
        return 40
                

complex_control_flow.compile()