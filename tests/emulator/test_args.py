"""Unit tests for guppylang.emulator._args argument validation helpers."""

from __future__ import annotations

import pytest
from guppylang.emulator._args import (
    EntrypointArgSpec,
    EntrypointArgValueError,
    validate_per_shot_args,
    validate_record,
)
from guppylang_internals.tys.builtin import (
    array_type,
    bool_type,
    int_type,
)
from guppylang_internals.tys.ty import NumericType

float_type = NumericType(NumericType.Kind.Float)


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
