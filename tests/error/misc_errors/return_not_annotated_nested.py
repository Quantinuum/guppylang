"""Added after: https://github.com/Quantinuum/guppylang/issues/2204"""
from guppylang import guppy


def _wrapper():
    @guppy
    def wrapper():
        return

    return wrapper


_wrapper().compile()
