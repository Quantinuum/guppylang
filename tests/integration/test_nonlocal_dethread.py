"""Tests for non-local (Dom-edge) de-threading of copyable values across CFG
basic blocks.

For a short-circuiting ``if b0 or b1 or ... or b(W-1):`` chain, guppy used to
thread every still-live boolean through the input/output signature of every
intervening basic block, giving O(W^2) total block-signature width (and O(W^2)
LLVM struct packing). Copyable values whose single definition strictly dominates
all their uses should instead be delivered via non-local Dom edges, keeping each
block signature O(1) and the total O(W).

Besides the positive O(W) win, these tests pin down that the gate stays
*conservative*: a value that is reassigned on one branch (multiple definitions)
or that is live across a loop back-edge must stay threaded, so a future
too-aggressive gate cannot silently bypass a value it shouldn't. The
array-packed variant is kept as a control so the block-width measurement can't be
fooled by single-wire packing.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

from hugr import ops

import guppylang_internals.compiler.cfg_compiler as cfg_compiler


def _compile_src(src: str, fn_name: str = "f", *, capture: bool = False):
    """Compile a guppy function from source, optionally capturing which places
    were de-threaded.

    Returns ``(package, dethreaded_names)`` where ``dethreaded_names`` is the set
    of variable names delivered via Dom edges (empty when ``capture`` is False).
    """
    dethreaded_names: set[str] = set()
    original = cfg_compiler.compute_dethread_info

    def spy(cfg, ctx):
        info = original(cfg, ctx)
        for place_id in info.ids:
            dethreaded_names.add(info.place[place_id].name)
        return info

    if capture:
        cfg_compiler.compute_dethread_info = spy
    try:
        tmp = Path(tempfile.mkdtemp()) / "mod.py"
        tmp.write_text(src)
        spec = importlib.util.spec_from_file_location(tmp.stem, tmp)
        assert spec is not None
        assert spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        pkg = getattr(mod, fn_name).compile_function()
    finally:
        cfg_compiler.compute_dethread_info = original
    return pkg, dethreaded_names


def _or_chain_src(w: int) -> str:
    """``if b0 or b1 or ... or b(W-1):`` over W separate scalar bools.

    The booleans are derived *inside* the function (as in the real user code,
    where they come from separate measurements) so that they are all defined in
    the entry block rather than being function parameters. This keeps W
    *separate* scalar booleans (not an array, which would pack them into a single
    wire and hide the threading) while exercising the cross-block threading that
    the entry function signature would otherwise mask.
    """
    defs = "\n".join(f"    b{i} = x > {i}" for i in range(w))
    terms = " or ".join(f"b{i}" for i in range(w))
    return f"""
from guppylang.decorator import guppy


@guppy
def f(x: int) -> int:
{defs}
    if {terms}:
        return 1
    return 0
"""


def _array_or_chain_src(w: int) -> str:
    """The same or-chain but with the bools packed into a single array wire."""
    elems = ", ".join(f"x > {i}" for i in range(w))
    terms = " or ".join(f"bs[{i}]" for i in range(w))
    return f"""
from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy
def f(x: int) -> int:
    bs = array({elems})
    if {terms}:
        return 1
    return 0
"""


def _compile_or_chain(w: int):
    pkg, _ = _compile_src(_or_chain_src(w))
    return pkg


def _block_input_widths(pkg) -> list[int]:
    hugr = pkg.modules[0]
    return [
        len(data.op.inputs)
        for _node, data in hugr.nodes()
        if isinstance(data.op, ops.DataflowBlock)
    ]


def test_or_chain_block_signatures_are_linear():
    """The per-block signature widths for an or-chain must stay O(1), so the
    total stays O(W) rather than the previous triangular O(W^2)."""
    for w in (8, 16, 32):
        widths = _block_input_widths(_compile_or_chain(w))
        assert widths, "expected some DataflowBlocks in the or-chain CFG"
        # De-threaded: no boolean is carried through a block signature it doesn't
        # need, so every block signature is a small constant width.
        assert max(widths) <= 2, (
            f"W={w}: max block-input width {max(widths)} grows with W "
            f"(widths={sorted(widths)})"
        )
        # Total across all blocks is linear in W, not quadratic.
        assert sum(widths) <= 2 * w, (
            f"W={w}: total block-input width {sum(widths)} looks super-linear "
            f"(widths={sorted(widths)})"
        )


def test_or_chain_bools_are_dethreaded():
    """The single-def, dominating or-chain booleans are the values we expect to
    deliver via Dom edges.

    ``b0`` is consumed in the entry block (it is the first branch predicate) so it
    never crosses a block signature and is not a de-thread candidate. Every later
    bool ``b1..b(W-1)`` is defined in the entry block yet used in a later block,
    so each must be de-threaded rather than threaded through the chain."""
    w = 8
    _pkg, dethreaded = _compile_src(_or_chain_src(w), capture=True)
    expected = {f"b{i}" for i in range(1, w)}
    assert expected <= dethreaded, (
        f"expected every crossing or-chain bool to be de-threaded, "
        f"missing {sorted(expected - dethreaded)} (de-threaded={sorted(dethreaded)})"
    )


def test_reassigned_bool_stays_threaded():
    """A bool reassigned on one branch has multiple definitions, so no single
    block dominates all uses: it must stay threaded (never de-threaded)."""
    src = """
from guppylang.decorator import guppy


@guppy
def f(x: int) -> int:
    b = x > 0
    if x > 3:
        b = x > 10
    if b:
        return 1
    return 0
"""
    _pkg, dethreaded = _compile_src(src, capture=True)
    assert "b" not in dethreaded, (
        f"reassigned bool `b` must stay threaded, but it was de-threaded "
        f"(de-threaded={sorted(dethreaded)})"
    )


def test_loop_carried_bool_stays_threaded():
    """A value live across a loop back-edge must stay threaded: de-threading it
    would deliver it once from the dominator, but the conservative gate keeps it
    on the block signatures."""
    src = """
from guppylang.decorator import guppy


@guppy
def f(x: int) -> int:
    b = x > 0
    acc = 0
    i = 0
    while i < 5:
        if b:
            acc = acc + 1
        i = i + 1
    return acc
"""
    _pkg, dethreaded = _compile_src(src, capture=True)
    assert "b" not in dethreaded, (
        f"loop-carried bool `b` must stay threaded, but it was de-threaded "
        f"(de-threaded={sorted(dethreaded)})"
    )


def test_array_packed_or_chain_is_a_control():
    """Non-regression control: when the bools are packed into a single array
    wire there is no per-bool threading to remove, so block widths are already
    O(1). This keeps the width-based measurement honest — small widths here come
    from packing, not from de-threading."""
    for w in (8, 16, 32):
        pkg, dethreaded = _compile_src(_array_or_chain_src(w), capture=True)
        widths = _block_input_widths(pkg)
        assert widths, "expected some DataflowBlocks in the array or-chain CFG"
        assert max(widths) <= 2, (
            f"W={w}: array-packed max block-input width {max(widths)} unexpectedly "
            f"grows with W (widths={sorted(widths)})"
        )
        # The single array wire is not a de-threadable scalar, so nothing named
        # `bs` is delivered via a Dom edge.
        assert "bs" not in dethreaded
