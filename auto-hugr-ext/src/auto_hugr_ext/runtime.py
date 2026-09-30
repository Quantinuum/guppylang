"""Runtime helpers used by generated Guppy modules."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import TYPE_CHECKING

from guppylang_internals.checker.core import Globals
from guppylang_internals.engine import ENGINE
from guppylang_internals.tys.parsing import parse_parameter
from hugr.ext import Extension

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from types import FrameType

    from guppylang_internals.compiler.core import CompilerContext
    from guppylang_internals.tys.arg import Argument
    from guppylang_internals.tys.common import ToHugrContext
    from guppylang_internals.tys.param import Parameter
    from guppylang_internals.tys.subst import Inst
    from hugr import tys as ht
    from hugr.ops import DataflowOp, ExtOp


def load_extension(path: str | Path) -> Extension:
    """Load extension JSON and register it with Guppy's compiler."""
    extension = Extension.from_json(Path(path).read_text(encoding="utf-8"))
    if not any(
        ext.name == extension.name and ext.version == extension.version
        for ext in ENGINE.additional_extensions
    ):
        ENGINE.additional_extensions.append(extension)
    return extension


def auto_hugr_type(
    extension: Extension, type_name: str
) -> Callable[[Sequence[Argument], ToHugrContext], ht.Type]:
    """Return the type lowering function for a generated custom type."""

    def to_hugr(args: Sequence[Argument], ctx: object) -> ht.Type:
        return extension.get_type(type_name).instantiate(
            [arg.to_hugr(ctx) for arg in args]
        )

    return to_hugr


def auto_hugr_op(
    extension: Extension, op_name: str
) -> Callable[[ht.FunctionType, Inst, CompilerContext], DataflowOp]:
    """Return the compiler function for a generated HUGR operation."""

    def build_op(ty: ht.FunctionType, inst: Inst, ctx: object) -> ExtOp:
        return extension.get_op(op_name).instantiate(
            args=[arg.to_hugr(ctx) for arg in inst], concrete_signature=ty
        )

    return build_op


def type_params_from_source(source: str) -> list[Parameter]:
    """Parse PEP 695 parameters using the generated module's defining frame."""
    frame = inspect.currentframe()
    assert frame is not None
    assert frame.f_back is not None
    caller_frame: FrameType = frame.f_back
    module = ast.parse(source)
    class_node = next(node for node in module.body if isinstance(node, ast.ClassDef))
    globals = Globals(caller_frame)
    mapping: dict[str, Parameter] = {}
    params: list[Parameter] = []
    for idx, node in enumerate(class_node.type_params):
        param = parse_parameter(node, idx, globals, mapping)
        params.append(param)
        mapping[param.name] = param
    return params
