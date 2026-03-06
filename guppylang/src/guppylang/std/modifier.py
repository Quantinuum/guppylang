# TODO: NICOLA Here we need to implement the actual modifiers
class Example:
    def __enter__(self):
        print("enter")

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("exit")


from ..decorator import guppy


@guppy
class dagger:
    def __enter__(self):
        print("enter")

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("exit")
