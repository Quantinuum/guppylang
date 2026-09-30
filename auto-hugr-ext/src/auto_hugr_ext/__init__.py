"""Automatic HUGR extension generation from annotated Python declarations."""

# `guppylang_internals.decorator` and `guppylang` import each other, so the outer
# package has to be loaded first.
import guppylang as _guppylang

from auto_hugr_ext.decorators import ext_op, ext_type
from auto_hugr_ext.generate import generate_new_hugr_ext, register_extension
from auto_hugr_ext.runtime import (
    auto_hugr_op,
    auto_hugr_type,
    load_extension,
    type_params_from_source,
)

__all__ = [
    "auto_hugr_op",
    "auto_hugr_type",
    "ext_op",
    "ext_type",
    "generate_new_hugr_ext",
    "load_extension",
    "register_extension",
    "type_params_from_source",
]
