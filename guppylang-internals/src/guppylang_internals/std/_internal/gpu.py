from dataclasses import dataclass
from typing import ClassVar

from guppylang_internals.diagnostic import Error
from guppylang_internals.tys.ty import Type


@dataclass(frozen=True)
class GpuError(Error):
    title: ClassVar[str] = "GPU signature error"


@dataclass(frozen=True)
class FirstArgNotModule(GpuError):
    span_label: ClassVar[str] = (
        "First argument to GPU function should be a reference to a GPU module."
        " Found `{ty}` instead"
    )
    ty: Type


@dataclass(frozen=True)
class UnconvertibleType(GpuError):
    span_label: ClassVar[str] = (
        "GPU function signature contained an unsupported type: `{ty}`"
    )
    ty: Type
