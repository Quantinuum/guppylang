from dataclasses import dataclass

from hugr import ops
from hugr import tys as ht
from hugr import val as hv

from guppylang_internals.std._internal.compiler.tket_exts import BOOL_EXTENSION

BOOL_DEF = BOOL_EXTENSION.get_type("bool")
OpaqueBool = ht.ExtType(BOOL_DEF)


def read_bool() -> ops.ExtOp:
    return ops.ExtOp(
        BOOL_EXTENSION.get_op("read"),
        ht.FunctionType([OpaqueBool], [ht.Bool]),
    )


def make_opaque() -> ops.ExtOp:
    return ops.ExtOp(
        BOOL_EXTENSION.get_op("make_opaque"),
        ht.FunctionType([ht.Bool], [OpaqueBool]),
    )


def not_op() -> ops.ExtOp:
    return ops.ExtOp(
        BOOL_EXTENSION.get_op("not"),
        ht.FunctionType([OpaqueBool], [OpaqueBool]),
    )


@dataclass
class OpaqueBoolVal(hv.ExtensionValue):
    """Custom value for a boolean."""

    v: bool

    def to_value(self) -> hv.Extension:
        name = "ConstBool"
        payload = self.v
        return hv.Extension(name, typ=OpaqueBool, val=payload)

    def __str__(self) -> str:
        return f"{self.v}"


OPAQUE_TRUE = OpaqueBoolVal(True)
OPAQUE_FALSE = OpaqueBoolVal(False)
