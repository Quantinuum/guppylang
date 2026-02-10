from guppylang import guppy

@guppy
def complex_control_flow(a: int, b: int, c: bool) -> int:
    if a > 10:
        if b < 5:
            if c:
                i= 10
            else:
                x = a - b
        else:
            y = a + b
        i = 9
    else:
        return 40
                
                

complex_control_flow.compile()