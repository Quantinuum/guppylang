from guppylang import guppy


def _wrapper():
    @guppy
    def wrapper():
        return

    return wrapper


_wrapper().compile()
