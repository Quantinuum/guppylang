"""Check custom power method declarations and signatures."""

import importlib.util
import sys
from itertools import product

import pytest

from guppylang_internals.engine import CustomModifiedDefSignatureError
from guppylang_internals.error import GuppyError
from guppylang_internals.tys.errors import NonLinearOwnedError

POWER_METHODS = ("powered", "power_daggered", "ctrl_powered", "ctrl_power_daggered")


@pytest.fixture
def load_gate(tmp_path, monkeypatch):
    """Load actual source files so Guppy can inspect each class's AST."""

    def load(
        methods,
        call_decorator="@guppy",
        call_params="",
        call_args="q: qubit, x: int",
        extra_source="",
    ):
        source = (
            "from guppylang import guppy\n"
            "from guppylang.decorator import expected_qubits\n"
            "from guppylang.std.builtins import (\n"
            "    array, nat, power, dagger, control, owned\n)\n"
            "from guppylang.std.quantum import qubit\n\n"
            "@guppy.unitary\nclass gate:\n"
            f"    {call_decorator}\n"
            f"    def __call__{call_params}({call_args}) -> None:\n        pass\n\n"
            + methods
            + extra_source
        )
        path = tmp_path / "custom_power.py"
        path.write_text(source)
        spec = importlib.util.spec_from_file_location("custom_power", path)
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, "custom_power", module)
        spec.loader.exec_module(module)
        return module

    return load


def method(
    name, args=None, params=None, output="None", body="pass", decorator="@guppy"
):
    controlled = name.startswith("ctrl_") or name == "controlled"
    if params is None:
        params = "[c: nat]" if controlled else ""
    if args is None:
        args = "q: qubit, x: int"
        if controlled:
            args += ", controls: array[qubit, c]"
        if name in POWER_METHODS:
            args += ", exponent: nat"
    return (
        f"    {decorator}\n    def {name}{params}({args}) -> {output}:\n"
        f"        {body}\n\n"
    )


@pytest.mark.parametrize("present", product((False, True), repeat=4))
@pytest.mark.parametrize(
    "base",
    [(), ("daggered",), ("controlled",), ("daggered", "controlled", "ctrl_daggered")],
)
def test_power_methods_have_no_combination_requirements(load_gate, present, base):
    """Check every subset of power methods alongside valid base custom methods.

    No power variant should require another custom method to be provided: the
    compiler can repeat the unpowered implementation. Checking the class itself
    also validates methods that are not called by any entry point."""
    names = [
        *base,
        *(name for name, yes in zip(POWER_METHODS, present, strict=True) if yes),
    ]
    module = load_gate("".join(method(name) for name in names))
    module.gate.check()


@pytest.mark.parametrize("name", POWER_METHODS)
@pytest.mark.parametrize(
    "invalid",
    [
        "missing_power",
        "wrong_power",
        "power_not_last",
        "extra_input",
        "wrong_input",
        "wrong_output",
        "wrong_ownership",
        "extra_parameter",
        "missing_input",
        "owned_power",
    ],
)
def test_power_signature_errors(load_gate, name, invalid):
    """Reject incompatible signatures for each of the four power variants.

    Mutations cover missing, misplaced, mistyped, or extra arguments; mismatched
    outputs and ownership; and additional generic parameters. The exponent must
    be a final runtime nat. Applying owned to that classical type is rejected by
    annotation parsing before custom-signature checking."""
    controlled = name.startswith("ctrl_")
    inputs = ["q: qubit", "x: int"]
    if controlled:
        inputs.append("controls: array[qubit, c]")
    inputs.append("exponent: nat")
    params = "[c: nat]" if controlled else ""
    output = "None"
    if invalid == "missing_power":
        inputs.pop()
    elif invalid == "wrong_power":
        inputs[-1] = "exponent: int"
    elif invalid == "power_not_last":
        inputs[-1], inputs[-2] = inputs[-2], inputs[-1]
    elif invalid == "extra_input":
        inputs.insert(0, "extra: bool")
    elif invalid == "wrong_input":
        inputs[1] = "x: float"
    elif invalid == "wrong_output":
        output = "int"
    elif invalid == "wrong_ownership":
        inputs[0] = "q: qubit @owned"
    elif invalid == "extra_parameter":
        params = "[c: nat, m: nat]" if controlled else "[m: nat]"
    elif invalid == "missing_input":
        inputs.pop(0)
    elif invalid == "owned_power":
        inputs[-1] = "exponent: nat @owned"
    module = load_gate(method(name, ", ".join(inputs), params, output))
    with pytest.raises(GuppyError) as exc:
        module.gate.check()
    if invalid == "owned_power":
        assert isinstance(exc.value.error, NonLinearOwnedError)
        return
    assert isinstance(exc.value.error, CustomModifiedDefSignatureError)
    assert exc.value.error.implementation == name
    assert "nat" in exc.value.error.expected_signature


@pytest.mark.parametrize("name", POWER_METHODS)
@pytest.mark.parametrize(
    "invalid", ["not_guppy", "unitary_flags", "expected_qubits", "body"]
)
def test_power_method_errors(load_gate, name, invalid):
    """Reject invalid declarations and bodies even for unused power methods.

    Every variant must be a Guppy function, may not declare its own unitary flags
    or expected-qubit metadata, and must have a well-typed body. Only __call__
    may supply those class-level annotations."""
    decorator = {
        "not_guppy": "",
        "unitary_flags": "@guppy(unitary=True)",
        "expected_qubits": "@guppy\n    @expected_qubits(1)",
        "body": "@guppy",
    }[invalid]
    body = "missing_name(q)" if invalid == "body" else "pass"
    with pytest.raises(GuppyError):
        load_gate(method(name, body=body, decorator=decorator)).gate.check()


@pytest.mark.parametrize("name", ["ctrl_powered", "ctrl_power_daggered"])
@pytest.mark.parametrize(
    "controls",
    [
        "controls: array[int, c]",
        "controls: array[qubit, 2]",
        "controls: array[qubit, c] @owned",
        "controls: qubit",
    ],
)
def test_power_control_signature_errors(load_gate, name, controls):
    """Require a borrowed, generically sized qubit array before the exponent.

    Both controlled power variants must reject classical arrays, fixed control
    counts, owned control arrays, and individual qubits. These errors must be
    reported as incompatible custom signatures rather than body errors."""
    module = load_gate(method(name, f"q: qubit, x: int, {controls}, exponent: nat"))
    with pytest.raises(GuppyError) as exc:
        module.gate.check()
    assert isinstance(exc.value.error, CustomModifiedDefSignatureError)
