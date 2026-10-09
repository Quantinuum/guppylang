# mypy: disable-error-code="empty-body, no-untyped-def"
"""Python builtins that are not supported yet"""

from guppylang_internals.decorator import custom_function
from guppylang_internals.std._internal.checker import UnsupportedChecker


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def aiter(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def all(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def anext(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def any(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def bin(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def breakpoint(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def bytearray(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def bytes(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def chr(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def classmethod(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def compile(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def complex(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def delattr(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def dict(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def dir(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def enumerate(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def eval(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def exec(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def filter(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def format(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def frozenset(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def getattr(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def globals(): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def hasattr(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def hash(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def help(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def hex(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def id(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def input(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def isinstance(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def issubclass(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def iter(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def locals(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def map(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def max(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def memoryview(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def min(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def next(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def object(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def oct(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def open(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def ord(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def print(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def property(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def repr(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def reversed(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def set(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def setattr(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def slice(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def sorted(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def sum(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def super(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def type(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def vars(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def zip(x): ...


@custom_function(checker=UnsupportedChecker(), higher_order_value=False, effects=())
def __import__(x): ...
