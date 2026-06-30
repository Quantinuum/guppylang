"""Support for runtime arguments to emulator entrypoint functions.

A Guppy execution entrypoint is normally required to take no inputs. To support
*runtime arguments* (e.g. for variational workflows where the same program is run
many times with different parameters), the emulator compiles an entrypoint with
parameters by *wrapping* it:

* the wrapper takes no inputs,
* for each parameter it reads the value at runtime via the ``tket.argument``
  ``read_arg`` op (tagged with the parameter name), and
* it calls the original entrypoint with those values.

Argument *values* are supplied at run time through selene's ``ArgProvider`` (see
:meth:`EmulatorInstance.run <guppylang.emulator.EmulatorInstance.run>` and
:meth:`run_per_shot <guppylang.emulator.EmulatorInstance.run_per_shot>`), keyed by
the parameter name.

This is currently an emulator-only (selene) feature: the ``read_arg`` op is only
lowered by the selene compiler, and argument values are provided through selene's
``ArgProvider``.

Only a restricted set of argument types is supported: ``bool``, signed ``int``,
``float``, and (one-dimensional) arrays of those. Unsigned ``nat`` is deliberately
not supported so that a single generic ``read_arg`` op suffices without signedness
ambiguity; take an ``int`` and convert in-script instead.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import tket_exts
from guppylang_internals.std._internal.compiler.array import (
    standard_array_type,
    std_array_to_array,
)
from guppylang_internals.tys.builtin import (
    get_array_length,
    get_element_type,
    is_array_type,
    is_bool_type,
)
from guppylang_internals.tys.const import ConstValue
from guppylang_internals.tys.ty import NumericType
from hugr import Wire, ops
from hugr import tys as ht
from hugr.build.function import Function
from hugr.std.collections.borrow_array import EXTENSION as BORROW_ARRAY_EXT

if TYPE_CHECKING:
    from collections.abc import Mapping

    from guppylang_internals.tys.ty import Type
    from hugr.hugr import Hugr
    from hugr.package import Package

_BORROW_ARRAY_DEF = BORROW_ARRAY_EXT.types["borrow_array"]

#: Name of the no-input wrapper function generated around the original entrypoint
#: when runtime arguments are injected via ``read_arg``.
_ARGS_WRAPPER_ENTRYPOINT_NAME = "__entrypoint_with_args"

# Keep in sync with `ArgValue`.
_SUPPORTED_ARG_TYPES_MSG = (
    "`bool`, `int`, `float`, and (one-dimensional) arrays of those"
)

#: Python value types accepted as entrypoint arguments.
#: Sequences (lists, tuples, numpy arrays, etc.) are accepted for array arguments
#: and converted to ``list`` before being passed to the selene argument provider.
ArgValue = int | float | bool | Sequence[int] | Sequence[float] | Sequence[bool]


@dataclass(frozen=True)
class EntrypointArgSpec:
    """A single runtime argument expected by a wrapped entrypoint."""

    name: str
    ty: Type


class EntrypointArgValueError(ValueError):
    """Raised when runtime argument values don't match the entrypoint signature."""


def _is_supported_scalar(ty: Type) -> bool:
    if is_bool_type(ty):
        return True
    if isinstance(ty, NumericType):
        return ty.kind in (NumericType.Kind.Int, NumericType.Kind.Float)
    return False


def _is_supported_arg_type(ty: Type) -> bool:
    if _is_supported_scalar(ty):
        return True
    if is_array_type(ty):
        return _is_supported_scalar(get_element_type(ty))
    return False


def unsupported_arg_reason(ty: Type) -> str | None:
    """Return ``None`` if ``ty`` is a supported argument type, otherwise a
    human-readable explanation of why it is not."""
    if _is_supported_arg_type(ty):
        return None
    if isinstance(ty, NumericType) and ty.kind is NumericType.Kind.Nat:
        return (
            "Unsigned `nat` arguments are not supported as entrypoint arguments. "
            "Use a signed `int` argument and convert in your program if needed."
        )
    if is_array_type(ty):
        elem = get_element_type(ty)
        if is_array_type(elem):
            return "Nested arrays are not supported as entrypoint arguments."
        if isinstance(elem, NumericType) and elem.kind is NumericType.Kind.Nat:
            return (
                "Arrays of unsigned `nat` are not supported as entrypoint arguments. "
                "Use a signed `int` element and convert in your program if needed."
            )
        return (
            f"Arrays of `{elem}` are not supported as entrypoint arguments. "
            f"Supported element types are {_SUPPORTED_ARG_TYPES_MSG}."
        )
    return (
        f"Type `{ty}` is not supported as an entrypoint argument. "
        f"Supported types are {_SUPPORTED_ARG_TYPES_MSG}."
    )


def _array_length(ty: Type) -> int | None:
    """Return the (concrete) length of an array type, or ``None`` if unknown."""
    length = get_array_length(ty)
    if isinstance(length, ConstValue) and isinstance(length.value, int):
        return length.value
    return None


def _value_error(ty: Type, value: object) -> str | None:
    """Return ``None`` if ``value`` is a valid argument of guppy type ``ty``,
    otherwise a human-readable reason why it is not."""
    if is_bool_type(ty):
        return None if isinstance(value, bool) else "expected a `bool`"
    if isinstance(ty, NumericType):
        match ty.kind:
            case NumericType.Kind.Int:
                if isinstance(value, bool):
                    return "expected an `int`, got a `bool`"
                return None if isinstance(value, int) else "expected an `int`"
            case NumericType.Kind.Float:
                if isinstance(value, bool):
                    return "expected a `float`, got a `bool`"
                return None if isinstance(value, (int, float)) else "expected a `float`"
    if is_array_type(ty):
        elem = get_element_type(ty)
        n = _array_length(ty)
        # str and bytes are Sequence subtypes in Python's ABC but are not valid
        # array arguments; exclude them so they fall through to the error below.
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            return f"expected an array of length {n}"
        # TODO: selene's ArgProvider currently rejects empty lists; this restriction
        # is expected to be lifted in https://github.com/Quantinuum/selene/pull/187.
        if n is not None and len(value) != n:
            return f"expected an array of length {n}, got {len(value)}"
        for i, item in enumerate(value):
            reason = _value_error(elem, item)
            if reason is not None:
                return f"array element {i}: {reason}"
        return None
    return f"unsupported argument type `{ty}`"


def validate_record(
    specs: Sequence[EntrypointArgSpec],
    record: Mapping[str, object],
    *,
    shot: int | None = None,
) -> None:
    """Validate a single argument record against the entrypoint signature.

    Raises :exc:`EntrypointArgValueError` if any argument is missing, unexpected,
    or has the wrong value type. ``shot`` is included in error messages when
    validating per-shot records.
    """
    where = f" for shot {shot}" if shot is not None else ""
    expected = {spec.name for spec in specs}
    given = set(record)
    if missing := sorted(expected - given):
        raise EntrypointArgValueError(
            f"Missing value(s){where} for entrypoint argument(s): "
            + ", ".join(f"`{name}`" for name in missing)
        )
    if extra := sorted(given - expected):
        raise EntrypointArgValueError(
            f"Unexpected entrypoint argument(s){where}: "
            + ", ".join(f"`{name}`" for name in extra)
        )
    for spec in specs:
        reason = _value_error(spec.ty, record[spec.name])
        if reason is not None:
            raise EntrypointArgValueError(
                f"Invalid value{where} for entrypoint argument `{spec.name}`: {reason}"
            )


def validate_per_shot_args(
    specs: Sequence[EntrypointArgSpec],
    per_shot: Sequence[Mapping[str, object]],
) -> None:
    """Validate a list of per-shot argument records against the signature."""
    if not per_shot:
        raise EntrypointArgValueError(
            "`run_per_shot` requires at least one shot's arguments."
        )
    for shot, record in enumerate(per_shot):
        validate_record(specs, record, shot=shot)


def wrap_entrypoint_with_args(package: Package, arg_names: Sequence[str]) -> None:
    """Rewrite the first module entrypoint with inputs in ``package`` to take no inputs.

    Iterates over modules in ``package``; rewrites the entrypoint of the first module
    whose entrypoint has input parameters. The original entrypoint ``f(a, b, ...)``
    is replaced by a no-input wrapper that reads each argument at runtime (via
    ``read_arg``, tagged with the corresponding name from ``arg_names``) and calls
    ``f``.

    Mutates ``package`` in place.
    """

    def read_arg_wire(wrapper: Function, name: str, ty: ht.Type) -> Wire:
        """Read a single runtime argument, bridging array representations.

        Entrypoint array parameters are lowered to ``borrow_array``, but the
        ``read_arg`` extern fills a standard ``array``. For arrays we therefore read
        a standard ``array`` and convert it to the ``borrow_array`` the entrypoint
        expects (the mirror of how the result compiler converts the other way).
        """
        if isinstance(ty, ht.ExtType) and ty.type_def is _BORROW_ARRAY_DEF:
            length_arg, elem_arg = ty.args
            assert isinstance(elem_arg, ht.TypeTypeArg)
            elem_ty = elem_arg.ty
            std_ty = standard_array_type(elem_ty, length_arg)
            std_wire = wrapper.add_op(tket_exts.argument.read_arg(name, std_ty))[0]
            return wrapper.add_op(std_array_to_array(elem_ty, length_arg), std_wire)[0]
        return wrapper.add_op(tket_exts.argument.read_arg(name, ty))[0]

    def _has_inputs(module: Hugr[Any]) -> bool:
        op = module[module.entrypoint].op
        return isinstance(op, ops.FuncDefn) and len(op.inputs) > 0

    module = next((m for m in package.modules if _has_inputs(m)), None)
    if module is None:
        raise ValueError("No entrypoint with input parameters found in package.")

    entrypoint = module.entrypoint
    op = module[entrypoint].op
    assert isinstance(op, ops.FuncDefn), "entrypoint must be a function definition"
    input_types = list(op.inputs)
    output_types = list(op.signature.body.output)
    if len(arg_names) != len(input_types):
        raise ValueError(
            "Mismatch between entrypoint parameter names "
            f"({len(arg_names)}) and HUGR inputs ({len(input_types)})."
        )

    wrapper = Function.new_nested(
        ops.FuncDefn(_ARGS_WRAPPER_ENTRYPOINT_NAME, [], visibility="Public"),
        module,
        module.module_root,
    )
    arg_wires = [
        read_arg_wire(wrapper, name, ty)
        for name, ty in zip(arg_names, input_types, strict=True)
    ]
    call_node = wrapper.call(entrypoint, *arg_wires)
    wrapper.set_outputs(*(call_node[i] for i in range(len(output_types))))
    module.entrypoint = wrapper.parent_node
