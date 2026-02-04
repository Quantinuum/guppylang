# mypy: disable-error-code="empty-body, no-untyped-def"
"""Python builtins that are not supported yet"""

from guppylang_internals.decorator import custom_function
from guppylang_internals.std._internal.checker import UnsupportedChecker


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def aiter(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def all(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def anext(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def any(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def bin(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def breakpoint(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def bytearray(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def bytes(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def chr(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def classmethod(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def compile(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def complex(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def delattr(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def dict(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def dir(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def enumerate(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def eval(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def exec(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def filter(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def format(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def frozenset(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def getattr(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def globals(): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def hasattr(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def hash(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def help(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def hex(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def id(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def input(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def isinstance(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def issubclass(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def iter(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def locals(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def map(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def max(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def memoryview(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def min(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def next(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def object(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def oct(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def open(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def ord(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def print(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def property(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def repr(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def reversed(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def set(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def setattr(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def slice(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def sorted(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def staticmethod(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def sum(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def super(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def type(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def vars(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def zip(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False)
def __import__(x): ...
