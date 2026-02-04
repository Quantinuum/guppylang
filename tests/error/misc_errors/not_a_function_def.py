from guppylang.decorator import guppy


f = lambda x: x
f = guppy(f)

f.compile()
