"""Custom power methods: checking and initial HUGR, before ModifierPass."""

import importlib.util
import sys
from itertools import product

import pytest
from hugr.ops import FuncDefn

from guppylang_internals.checker.modifier import CustomModifierKind
from guppylang_internals.engine import ENGINE, CustomModifiedDefSignatureError
from guppylang_internals.error import GuppyError
from guppylang_internals.metadata.common import NumControlQubits
from guppylang_internals.nodes import CheckedModifiedBlock
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


@pytest.mark.parametrize("present", product((False, True), repeat=4))
def test_power_initial_compilation(load_gate, present, validate):
    """Compile each subset of power overrides without running ModifierPass.

    Each requested override is used in its own single-call block with the
    corresponding control/dagger modifiers. Validate initial HUGR and its custom
    links, including the concrete control count. A plain power call also covers
    automatic repetition when no powered override is supplied."""
    names = [name for name, yes in zip(POWER_METHODS, present, strict=True) if yes]
    calls = ""
    for name in names:
        modifiers = ["power(exponent)"]
        if "daggered" in name:
            modifiers.append("dagger")
        if name.startswith("ctrl_"):
            modifiers.append("control(controls)")
        calls += f"    with {', '.join(modifiers)}:\n        gate(q, x)\n"
    # Also exercise automatic power generation when no override is supplied.
    calls += "    with power(exponent):\n        gate(q, x)\n"
    module = load_gate(
        "".join(method(name) for name in names),
        "@guppy(unitary=True)",
        extra_source=(
            "\n@guppy\ndef main(q: qubit, x: int, "
            "controls: array[qubit, 2], exponent: nat) -> None:\n"
        )
        + calls,
    )
    module.main.check()
    package = module.main.with_minimal_opt().compile_function()
    validate(package, export=False)
    definitions = {
        data.op.f_name: data
        for _, data in package.modules[0].nodes()
        if isinstance(data.op, FuncDefn)
    }
    for name in names:
        key = "tket." + name
        [metadata] = [
            data.metadata for data in definitions.values() if key in data.metadata
        ]
        links = metadata[key]
        if name.startswith("ctrl_"):
            assert len(links) == 1
            assert definitions[links[0]].metadata[NumControlQubits.KEY] == 2
        else:
            assert isinstance(links, str)
            assert links in definitions


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


@pytest.mark.parametrize("name", POWER_METHODS)
def test_generic_power_methods(load_gate, name, validate):
    """Preserve parent generics when specializing each custom power variant.

    The parent operates on a generic qubit array. Controlled variants deliberately
    put their extra control-count parameter before the parent parameter, testing
    normalization and concrete specialization. Compile and validate only initial
    HUGR, leaving runtime exponent handling to the future ModifierPass update."""
    controlled = name.startswith("ctrl_")
    args = "qs: array[qubit, m], x: int"
    if controlled:
        args += ", controls: array[qubit, c]"
    args += ", exponent: nat"
    params = "[c: nat, m: nat]" if controlled else "[m: nat]"
    modifiers = ["power(exponent)"]
    if controlled:
        modifiers.append("control(controls)")
    if "daggered" in name:
        modifiers.append("dagger")
    module = load_gate(
        method(name, args, params),
        "@guppy(unitary=True)",
        call_params="[m: nat]",
        call_args="qs: array[qubit, m], x: int",
        extra_source=(
            "\n@guppy\ndef main(qs: array[qubit, 3], x: int, "
            "controls: array[qubit, 2], exponent: nat) -> None:\n"
            f"    with {', '.join(modifiers)}:\n        gate(qs, x)\n"
        ),
    )
    module.main.check()
    validate(module.main.with_minimal_opt().compile_function(), export=False)


@pytest.mark.parametrize("name", POWER_METHODS)
@pytest.mark.parametrize("call_count", [1, 2])
@pytest.mark.parametrize("nested", [False, True])
def test_power_dispatch_requires_single_call(
    load_gate, name, call_count, nested, validate
):
    """Select powered overrides only for blocks containing exactly one call.

    All seven custom methods are available, so lookup could otherwise choose the
    powered variant incorrectly. Two calls to the same gate must use its ordinary
    dagger/control override and repeat the complete sequence. Check both a single
    combined with statement and a power block wrapping a control/dagger block;
    modifier constructors themselves must not be counted as body calls. Verify
    registered contexts and initial HUGR, without running modifier resolution.
    """
    other_modifiers = []
    if "daggered" in name:
        other_modifiers.append("dagger")
    if name.startswith("ctrl_"):
        other_modifiers.append("control(controls)")
    if nested and other_modifiers:
        block = "    with power(exponent):\n"
        block += f"        with {', '.join(other_modifiers)}:\n"
        indent = "            "
    else:
        block = f"    with {', '.join(['power(exponent)', *other_modifiers])}:\n"
        indent = "        "
    block += (indent + "gate(q, x)\n") * call_count
    base_names = ["daggered", "controlled", "ctrl_daggered"]
    module = load_gate(
        "".join(method(kind) for kind in [*base_names, *POWER_METHODS]),
        extra_source=(
            "\n@guppy\ndef main(q: qubit, x: int, "
            "controls: array[qubit, 2], exponent: nat) -> None:\n" + block
        ),
    )
    module.main.check()
    expected_name = (
        name
        if call_count == 1
        else {
            "powered": None,
            "power_daggered": "daggered",
            "ctrl_powered": "controlled",
            "ctrl_power_daggered": "ctrl_daggered",
        }[name]
    )
    assert {use.kind.value for use in ENGINE.custom_uses_by_mono_def.values()} == (
        {expected_name} if expected_name else set()
    )
    contexts = ENGINE.local_modifiers_by_edge[
        (module.main.id, ()), (module.gate.id, ())
    ]
    assert all(context.powered for context in contexts)
    assert {context.power_customizable for context in contexts} == {call_count == 1}
    checked_main = ENGINE.checked[module.main.id, ()]
    blocks = [
        stmt
        for bb in checked_main.cfg.bbs
        for stmt in bb.statements
        if isinstance(stmt, CheckedModifiedBlock)
    ]
    assert len(blocks) == 1
    assert blocks[0].has_single_call == (call_count == 1)
    validate(module.main.with_minimal_opt().compile_function(), export=False)


def test_power_eligibility_is_recorded_per_block(load_gate, validate):
    """Keep single-call and multi-call contexts separate for the same call edge.

    The first block powers one gate call and requires ctrl_power_daggered. The
    second powers a sequence of two calls and requires ctrl_daggered instead.
    Both contexts target the same monomorphized gate, so the edge must retain two
    distinct labels and both custom implementations must reach initial HUGR.
    """
    module = load_gate(
        "".join(
            method(name)
            for name in [
                "daggered",
                "controlled",
                "ctrl_daggered",
                *POWER_METHODS,
            ]
        ),
        extra_source=(
            "\n@guppy\ndef main(q: qubit, x: int, "
            "controls: array[qubit, 2], exponent: nat) -> None:\n"
            "    with control(controls), dagger, power(exponent):\n"
            "        gate(q, x)\n"
            "    with control(controls), dagger, power(exponent):\n"
            "        gate(q, x)\n        gate(q, x)\n"
        ),
    )
    module.main.check()
    assert {use.kind for use in ENGINE.custom_uses_by_mono_def.values()} == {
        CustomModifierKind.CTRL_DAGGERED,
        CustomModifierKind.CTRL_POWER_DAGGERED,
    }
    contexts = ENGINE.local_modifiers_by_edge[
        (module.main.id, ()), (module.gate.id, ())
    ]
    assert {context.power_customizable for context in contexts} == {False, True}
    validate(module.main.with_minimal_opt().compile_function(), export=False)


@pytest.mark.parametrize("helper_calls", [1, 2])
def test_power_is_not_distributed_through_helpers(load_gate, helper_calls, validate):
    """Repeat a helper as a whole rather than powering each call inside it.

    The modifier block has one helper call, but no custom helper implementation
    consumes its exponent. Control and dagger still reach each gate inside the
    helper; power is not eligible for custom dispatch there. This remains true
    even for a helper with one call, since lookup has crossed a function boundary.
    """
    module = load_gate(
        "".join(
            method(name)
            for name in [
                "daggered",
                "controlled",
                "ctrl_daggered",
                *POWER_METHODS,
            ]
        ),
        extra_source=(
            "\n@guppy(unitary=True)\ndef helper(q: qubit, x: int) -> None:\n"
            + "    gate(q, x)\n" * helper_calls
            + "\n@guppy\ndef main(q: qubit, x: int, "
            "controls: array[qubit, 2], exponent: nat) -> None:\n"
            "    with control(controls), dagger, power(exponent):\n"
            "        helper(q, x)\n"
        ),
    )
    module.main.check()
    assert {use.kind for use in ENGINE.custom_uses_by_mono_def.values()} == {
        CustomModifierKind.CTRL_DAGGERED,
    }
    validate(module.main.with_minimal_opt().compile_function(), export=False)


@pytest.mark.parametrize(
    "body",
    [
        "        pass\n",
        "        for _ in range(2):\n            gate(q, x)\n",
        "        if x > 0:\n            gate(q, x)\n",
        "        gate(q, identity(x))\n",
    ],
)
def test_power_requires_one_unconditional_body_call(load_gate, body, validate):
    """Exclude empty bodies, conditional/repeated calls, and argument calls.

    A single call written in a loop or branch does not execute exactly once per
    block iteration. Likewise gate(q, identity(x)) contains two calls despite
    being one expression statement. None of these bodies can be replaced by the
    gate's custom powered method. Preserve the block's eligibility flag through
    checking and validate the unreduced HUGR with ordinary block repetition.
    """
    module = load_gate(
        method("powered"),
        extra_source=(
            "\n@guppy\ndef identity(x: int) -> int:\n    return x\n"
            "\n@guppy\ndef main(q: qubit, x: int, exponent: nat) -> None:\n"
            "    with power(exponent):\n" + body
        ),
    )
    module.main.check()
    assert not ENGINE.custom_uses_by_mono_def
    checked_main = ENGINE.checked[module.main.id, ()]
    [block] = [
        stmt
        for bb in checked_main.cfg.bbs
        for stmt in bb.statements
        if isinstance(stmt, CheckedModifiedBlock)
    ]
    assert not block.has_single_call
    validate(module.main.with_minimal_opt().compile_function(), export=False)


def test_inner_power_can_be_custom_inside_multicall_power(load_gate, validate):
    """Keep an inner power eligible while its enclosing sequence is repeated.

    The outer power block has two gate calls, one inside an inner power block.
    Only the inner block may select gate.powered. The direct call stays unpowered,
    and both contexts must survive on their shared graph edge. This ensures an
    ineligible outer power does not suppress an independently eligible inner one.
    """
    module = load_gate(
        method("powered"),
        extra_source=(
            "\n@guppy\ndef main(q: qubit, x: int, exponent: nat) -> None:\n"
            "    with power(exponent):\n"
            "        gate(q, x)\n"
            "        with power(exponent):\n            gate(q, x)\n"
        ),
    )
    module.main.check()
    contexts = ENGINE.local_modifiers_by_edge[
        (module.main.id, ()), (module.gate.id, ())
    ]
    assert {context.power_customizable for context in contexts} == {False, True}
    assert {use.kind for use in ENGINE.custom_uses_by_mono_def.values()} == {
        CustomModifierKind.POWERED,
    }
    validate(module.main.with_minimal_opt().compile_function(), export=False)


def test_multicall_power_uses_unpowered_methods_for_each_gate(load_gate, validate):
    """Require ctrl_daggered for both distinct gates in one powered sequence.

    Each gate provides all seven custom methods. Repeating the pair must preserve
    their interleaving, so neither ctrl_power_daggered method may be selected.
    Assert that both parent definitions get their own ctrl_daggered use and
    validate the initial HUGR, without running the unfinished ModifierPass.
    """
    methods = "".join(
        method(name)
        for name in [
            "daggered",
            "controlled",
            "ctrl_daggered",
            *POWER_METHODS,
        ]
    )
    module = load_gate(
        methods,
        extra_source=(
            "\n@guppy.unitary\nclass other_gate:\n"
            "    @guppy\n    def __call__(q: qubit, x: int) -> None:\n        pass\n\n"
            + methods
            + "\n@guppy\ndef main(q: qubit, x: int, "
            "controls: array[qubit, 2], exponent: nat) -> None:\n"
            "    with control(controls), dagger, power(exponent):\n"
            "        gate(q, x)\n        other_gate(q, x)\n"
        ),
    )
    module.main.check()
    uses = list(ENGINE.custom_uses_by_mono_def.values())
    assert len(uses) == 2
    assert {use.kind for use in uses} == {CustomModifierKind.CTRL_DAGGERED}
    assert {use.unmodified_callee[0] for use in uses} == {
        module.gate.id,
        module.other_gate.id,
    }
    validate(module.main.with_minimal_opt().compile_function(), export=False)
