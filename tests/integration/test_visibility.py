from hugr.tys import Visibility
from hugr.ops import FuncDefn, FuncDecl

from guppylang import guppy
from guppylang.defs import GuppyFunctionDefinition


def _visibility(func: GuppyFunctionDefinition) -> Visibility:
    hugr = func.compile_function().modules[0]
    compiled_nodes: list[FuncDefn | FuncDecl] = [
        n.op
        for n in hugr.values()
        if isinstance(n.op, (FuncDefn, FuncDecl)) and n.op.f_name == func.wrapped.name
    ]
    if len(compiled_nodes) == 0:
        raise RuntimeError(f"No node found for function {func.wrapped.name}")
    if len(compiled_nodes) > 1:
        raise RuntimeError(
            f"Multiple nodes found for function {func.wrapped.name}: {compiled_nodes}"
        )

    return compiled_nodes[0].visibility


def test_definition_visibility_annotated():
    """Asserts that annotated visibilities are correctly passed to the HUGR nodes."""

    @guppy(public=True)
    def public_func() -> None:
        pass

    @guppy(public=False)
    def private_func() -> None:
        pass

    assert _visibility(public_func) == "Public"
    assert _visibility(private_func) == "Private"


def test_definition_visibility_inferred():
    """Asserts that inferred visibilities are correctly passed to the HUGR nodes."""

    @guppy
    def public_func() -> None:
        pass

    @guppy
    def _private_func() -> None:
        pass

    assert _visibility(public_func) == "Public"
    assert _visibility(_private_func) == "Private"


def test_declaration_visibility_annotated():
    """Asserts that annotated visibilities are correctly passed to the HUGR nodes."""

    @guppy.declare(public=True)
    def public_func() -> None: ...
    @guppy.declare(public=False)
    def private_func() -> None: ...

    assert _visibility(public_func) == "Public"
    assert _visibility(private_func) == "Private"


def test_declaration_visibility_inferred():
    """Asserts that inferred visibilities are correctly passed to the HUGR nodes."""

    @guppy.declare
    def public_func() -> None: ...
    @guppy.declare
    def _private_func() -> None: ...

    assert _visibility(public_func) == "Public"
    assert _visibility(_private_func) == "Private"
