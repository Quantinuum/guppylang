from guppylang import guppy

@guppy
def while_loop(n: int, x: int, i: int) -> int:
    x  = 0
    while i < n:
        x = x + i
        i = i + 1
        
        return x
    

while_loop.check()