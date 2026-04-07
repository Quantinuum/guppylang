# class PyTest:
#     @classmethod
#     def default(self) -> "PyTest":
#         return PyTest()  #

#     def another(self) -> "PyTest":
#         return PyTest()
# from collections.abc import Callable

# from guppylang import guppy, qubit
# from guppylang.std.angles import angle
# from guppylang.std.quantum import discard, rx, ry


# @guppy.struct
# class Test:
#     rx_method: Callable[[qubit, angle], None]
#     ry_method: Callable[[qubit, angle], None]

#     @guppy
#     @staticmethod
#     def default() -> "Test":
#         return Test(rx, ry)

#     @guppy
#     def nonclass(self) -> None:
#         pass


# @guppy
# def main() -> None:
#     t = Test.default()
#     q = qubit()
#     t.rx_method(q, angle(0.1))
#     t.ry_method(q, angle(0.1))
#     t.default()
#     t.nonclass()
#     discard(q)


# print(main.emulator(1).run().results)
