from guppylang import guppy

@guppy.protocol
class Proto:
    @guppy.require
    def foo(self) -> None: ...

@guppy.struct
class Struct:
    @guppy
    def foo(self) -> None:
        return

@guppy
def bar() -> Proto:
    return Struct()

bar.compile_function()
