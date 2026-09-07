"""Tests for ``scripts/release/update_changelog.py``."""

from __future__ import annotations

import update_changelog as uc

BASE = """\
# Changelog

Intro prose that stays at the top.

## [1.0.0-a5](https://x/compare/a4...a5) (2026-06-15)

### Features

* Old feature ([#1](https://x/1))
"""

NEW_SECTION = """\
## [1.0.0-a6](https://x/compare/a5...a6) (2026-06-19)

### Features

* New feature ([#2](https://x/2))
"""


def test_insert_above_latest() -> None:
    out = uc.update_changelog(BASE, "1.0.0-a6", NEW_SECTION)
    lines = out.splitlines()
    # Intro preserved at the top.
    assert lines[0] == "# Changelog"
    assert "Intro prose that stays at the top." in out
    # New section comes before the previous one.
    assert out.index("1.0.0-a6") < out.index("1.0.0-a5")
    assert "New feature" in out
    assert "Old feature" in out


def test_regeneration_is_idempotent() -> None:
    once = uc.update_changelog(BASE, "1.0.0-a6", NEW_SECTION)
    twice = uc.update_changelog(once, "1.0.0-a6", NEW_SECTION)
    assert once == twice
    assert twice.count("1.0.0-a6") == NEW_SECTION.count("1.0.0-a6")


def test_replace_existing_draft() -> None:
    once = uc.update_changelog(BASE, "1.0.0-a6", NEW_SECTION)
    revised = NEW_SECTION.replace("New feature", "Revised feature")
    out = uc.update_changelog(once, "1.0.0-a6", revised)
    assert "Revised feature" in out
    assert "New feature" not in out
    assert out.count("## [1.0.0-a6]") == 1


def test_insert_into_changelog_without_versions() -> None:
    base = "# Changelog\n\nNothing released yet.\n"
    out = uc.update_changelog(base, "1.0", NEW_SECTION.replace("1.0.0-a6", "1.0"))
    assert "# Changelog" in out
    assert "1.0" in out


def test_replace_short_version_keeps_longer_prefixed_section() -> None:
    """Replacing the ``1.0`` draft must not also swallow the legacy ``1.0.0-a4`` section
    that shares its prefix."""
    base = (
        "# Changelog\n\n"
        "## [1.0](https://x)\n\n"
        "* draft 1.0 notes\n\n"
        "## [1.0.0-a4](https://x)\n\n"
        "* legacy alpha notes\n"
    )
    revised = "## [1.0](https://x)\n\n* revised 1.0 notes\n"
    out = uc.update_changelog(base, "1.0", revised)
    assert "revised 1.0 notes" in out
    assert "draft 1.0 notes" not in out
    # The legacy section below must be preserved untouched.
    assert "legacy alpha notes" in out
    assert out.count("## [1.0.0-a4]") == 1
