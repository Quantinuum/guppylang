from guppylang.decorator import guppy

@guppy(effects=[])
def pure_func(arr: array[int, 3]) -> int:
    return arr[0] + arr[1] + arr[2]

pure_func.compile_function()