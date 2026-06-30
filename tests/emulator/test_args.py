"""Unit tests for guppylang.emulator._args argument validation helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import pytest
from guppylang import guppy
from guppylang.emulator._args import (
    EntrypointArgSpec,
    EntrypointArgValueError,
    _is_supported_arg_type,
    unsupported_arg_reason,
    validate_per_shot_args,
    validate_record,
    wrap_entrypoint_with_args,
)
from guppylang.std.builtins import array, result
from guppylang_internals.tys.builtin import (
    array_type,
    bool_type,
    int_type,
    nat_type,
)
from guppylang_internals.tys.ty import NumericType
from hugr import ops

if TYPE_CHECKING:
    from hugr.hugr import Hugr

float_type = NumericType(NumericType.Kind.Float)


@pytest.mark.parametrize(
    "ty",
    [
        bool_type(),
        int_type(),
        float_type,
        array_type(int_type(), 3),
        array_type(float_type, 2),
        array_type(bool_type(), 5),
    ],
)
def test_supported_arg_types(ty: Any) -> None:
    assert _is_supported_arg_type(ty)
    assert unsupported_arg_reason(ty) is None


def test_nat_is_unsupported() -> None:
    reason = unsupported_arg_reason(nat_type())
    assert reason is not None
    assert "nat" in reason
    assert not _is_supported_arg_type(nat_type())


def test_nested_array_is_unsupported() -> None:
    ty = array_type(array_type(int_type(), 2), 3)
    reason = unsupported_arg_reason(ty)
    assert reason is not None
    assert "Nested arrays" in reason


def test_array_of_nat_is_unsupported() -> None:
    ty = array_type(nat_type(), 3)
    assert not _is_supported_arg_type(ty)
    assert unsupported_arg_reason(ty) is not None


def _specs() -> tuple[EntrypointArgSpec, ...]:
    return (
        EntrypointArgSpec("theta", float_type),
        EntrypointArgSpec("k", int_type()),
        EntrypointArgSpec("flag", bool_type()),
    )


def test_validate_record_ok() -> None:
    validate_record(_specs(), {"theta": 1.5, "k": 3, "flag": True})
    # ints are accepted for floats
    validate_record(_specs(), {"theta": 2, "k": 3, "flag": False})


def test_validate_record_missing() -> None:
    with pytest.raises(EntrypointArgValueError, match=r"Missing.*`flag`"):
        validate_record(_specs(), {"theta": 1.5, "k": 3})


def test_validate_record_extra() -> None:
    with pytest.raises(EntrypointArgValueError, match=r"Unexpected.*`extra`"):
        validate_record(_specs(), {"theta": 1.5, "k": 3, "flag": True, "extra": 1})


def test_validate_record_wrong_type() -> None:
    with pytest.raises(EntrypointArgValueError, match=r"`k`.*expected an `int`"):
        validate_record(_specs(), {"theta": 1.5, "k": "x", "flag": True})


def test_validate_record_bool_not_int() -> None:
    with pytest.raises(EntrypointArgValueError, match="got a `bool`"):
        validate_record(_specs(), {"theta": 1.5, "k": True, "flag": True})


def test_validate_array_args() -> None:
    specs = (EntrypointArgSpec("xs", array_type(int_type(), 3)),)
    validate_record(specs, {"xs": [1, 2, 3]})

    with pytest.raises(EntrypointArgValueError, match="length 3, got 2"):
        validate_record(specs, {"xs": [1, 2]})

    with pytest.raises(EntrypointArgValueError, match="length 3, got 0"):
        validate_record(specs, {"xs": []})

    with pytest.raises(EntrypointArgValueError, match="array element"):
        validate_record(specs, {"xs": [1, "x", 3]})


def test_validate_per_shot_args_ok() -> None:
    validate_per_shot_args(
        _specs(),
        [
            {"theta": 1.0, "k": 1, "flag": True},
            {"theta": 2.0, "k": 2, "flag": False},
        ],
    )


def test_validate_per_shot_args_empty() -> None:
    with pytest.raises(EntrypointArgValueError, match="at least one"):
        validate_per_shot_args(_specs(), [])


def test_validate_per_shot_args_reports_shot() -> None:
    with pytest.raises(EntrypointArgValueError, match="for shot 1"):
        validate_per_shot_args(
            _specs(),
            [
                {"theta": 1.0, "k": 1, "flag": True},
                {"theta": 2.0, "k": 2},
            ],
        )


def _is_ext_op(op: Any, qualified_name: str) -> bool:
    """True if `op` is the extension op with the given fully-qualified name."""
    return isinstance(op, ops.ExtOp) and op.op_def().qualified_name() == qualified_name


def _read_arg_output_types(module: Hugr[Any]) -> list[Any]:
    """Collect the output type of every `read_arg` op in a wrapped module."""
    return [
        ty
        for _node, data in module.nodes()
        if _is_ext_op(data.op, "tket.argument.read_arg")
        for ty in cast("ops.ExtOp", data.op).outer_signature().output
    ]


def _has_from_array_op(module: Hugr[Any]) -> bool:
    """True if the module contains a std->borrow `from_array` conversion op."""
    return any(
        _is_ext_op(data.op, "collections.borrow_arr.from_array")
        for _node, data in module.nodes()
    )


def test_wrap_bridges_array_to_standard_array() -> None:
    """Array params read a standard `array` and convert to `borrow_array`.

    The entrypoint expects a `borrow_array`, but the argreader extern fills a
    standard `array`. The wrapper must therefore read a standard `array` and
    insert a `from_array` conversion, mirroring the result compiler's bridge.
    """

    @guppy
    def main(xs: array[float, 3]) -> None:
        result("a", xs[0])

    package = main.compile_function()
    wrap_entrypoint_with_args(package, ["xs"])

    (out,) = _read_arg_output_types(package.modules[0])
    assert out.type_def.name == "array", (
        f"read_arg should output a standard `array`, got {out.type_def.name}"
    )
    assert _has_from_array_op(package.modules[0]), (
        "expected a std->borrow `from_array` conversion for the array argument"
    )
