"""Tests for ``scripts/release/render_pr_body.py``."""

from __future__ import annotations

import render_pr_body as rp


def test_render_block_contains_markers_and_sections() -> None:
    block = rp.render_block(
        [
            ("guppylang", "1.0.0-a6", "### Features\n\n* thing"),
            ("guppylang-internals", "1.6", "### Bug Fixes\n\n* fix"),
        ]
    )
    assert block.startswith(rp.BEGIN)
    assert block.endswith(rp.END)
    assert "guppylang" in block
    assert "1.0.0-a6" in block
    assert "guppylang-internals" in block
    assert "1.6" in block
    assert "* thing" in block
    assert "* fix" in block


def test_render_block_empty_section_placeholder() -> None:
    block = rp.render_block([("guppylang", "1.0.0-a6", "   ")])
    assert "_No changelog entry._" in block


def test_update_body_inserts_when_absent() -> None:
    body = "Some PR description.\n"
    block = rp.render_block([("guppylang", "1.0.0-a6", "* x")])
    out = rp.update_body(body, block)
    assert "Some PR description." in out
    assert rp.BEGIN in out
    assert rp.END in out


def test_update_body_replaces_in_place_idempotently() -> None:
    body = "Intro.\n"
    first = rp.update_body(body, rp.render_block([("guppylang", "1.0.0-a6", "* a")]))
    second = rp.update_body(first, rp.render_block([("guppylang", "1.0.0-a7", "* b")]))
    # The intro survives and only one preview block exists.
    assert second.count(rp.BEGIN) == 1
    assert second.count(rp.END) == 1
    assert "Intro." in second
    assert "1.0.0-a7" in second
    assert "1.0.0-a6" not in second
