from guppylang_internals.decorator import custom_function


@custom_function(effects=())
def foo(x): ...


foo.compile()
