# ruff: noqa: SIM211

from tests.util import compile_guppy


@compile_guppy
def no_return_if_exp_polarity(b: bool) -> int:
    if False if b else True:
        return 0
