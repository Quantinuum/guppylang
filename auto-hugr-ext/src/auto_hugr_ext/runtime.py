"""Runtime helpers used by generated Guppy modules."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import TYPE_CHECKING, cast

from guppylang.std.lang import Copy, Drop
from guppylang_internals.checker.core import Globals
from guppylang_internals.decorator import custom_type
from guppylang_internals.engine import DEF_STORE, ENGINE
from guppylang_internals.tys.param import Parameter, TypeParam
from guppylang_internals.tys.protocol import ProtocolInst
from hugr import tys as ht
from hugr.ext import Extension

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from guppylang.defs import GuppyDefinition
    from guppylang_internals.compiler.core import CompilerContext
    from guppylang_internals.definition.common import DefId
    from guppylang_internals.tys.arg import Argument
    from guppylang_internals.tys.common import ToHugrContext
    from guppylang_internals.tys.subst import Inst
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
    extension: Extension,
    type_name: str | None = None,
    *,
    copyable: bool = True,
    droppable: bool = True,
    params: Sequence[Parameter] | None = None,
) -> Callable[[type], GuppyDefinition]:
    """Decorate a class with its matching type definition from a HUGR extension."""

    def decorate(cls: type) -> GuppyDefinition:
        name = type_name or cls.__name__
        type_params = list(params) if params is not None else _class_type_params(cls)

        def to_hugr(args: Sequence[Argument], ctx: ToHugrContext) -> ht.Type:
            return extension.get_type(name).instantiate(
                [arg.to_hugr(ctx) for arg in args]
            )

        bound = ht.TypeBound.Copyable if copyable and droppable else ht.TypeBound.Linear
        definition = cast(
            "GuppyDefinition",
            custom_type(
                to_hugr,
                name=name,
                copyable=copyable,
                droppable=droppable,
                params=type_params,
                bound=bound,
            )(cls),
        )
        frame = inspect.currentframe()
        assert frame is not None
        assert frame.f_back is not None
        DEF_STORE.frames[definition.id] = frame.f_back
        return definition

    return decorate


def _class_type_params(cls: type) -> list[Parameter]:
    frame = inspect.currentframe()
    assert frame is not None
    assert frame.f_back is not None
    globals = Globals(frame.f_back)
    params: list[Parameter] = []
    for idx, py_param in enumerate(getattr(cls, "__type_params__", ())):
        bound = py_param.__bound__
        constraints = py_param.__constraints__
        copyable = bound is Copy or Copy in constraints
        droppable = bound is Drop or Drop in constraints
        implemented: list[ProtocolInst] = []
        unsupported = [
            candidate
            for candidate in ((bound,) if bound is not None else ())
            + tuple(constraints)
            if candidate not in (Copy, Drop)
        ]
        for candidate in unsupported:
            candidate_name = getattr(candidate, "__name__", None)
            resolved = globals[candidate_name] if candidate_name is not None else None
            definition: DefId | None = getattr(resolved, "id", None)
            if definition is None:
                raise TypeError(
                    f"Unsupported bound {candidate!r} "
                    f"for type parameter {py_param.__name__}"
                )
            implemented.append(ProtocolInst((), definition))
        params.append(
            TypeParam(
                idx,
                py_param.__name__,
                must_be_copyable=copyable,
                must_be_droppable=droppable,
                must_implement=implemented,
            )
        )
    return params


def auto_hugr_op(
    extension: Extension, op_name: str
) -> Callable[[ht.FunctionType, Inst, CompilerContext], DataflowOp]:
    """Return the compiler function for a generated HUGR operation."""

    def build_op(ty: ht.FunctionType, inst: Inst, ctx: object) -> ExtOp:
        return extension.get_op(op_name).instantiate(
            args=[arg.to_hugr(ctx) for arg in inst], concrete_signature=ty
        )

    return build_op
