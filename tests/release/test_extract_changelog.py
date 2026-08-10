"""Tests for ``scripts/release/extract_changelog.py``."""

from __future__ import annotations

import extract_changelog as ec
import pytest

CHANGELOG = """\
# Changelog

## A confusing header at the beginning

Some intro prose that must never appear in release notes.

## [1.0.0-a6](https://example.com/compare/a5...a6) (2026-06-19)

### Features

* Add a shiny new thing ([#1900](https://example.com/1900))

### Bug Fixes

* Fix an old thing ([#1899](https://example.com/1899))

## [1.0.0-a5](https://example.com/compare/a4...a5) (2026-06-15)

### Features

* An older feature ([#1850](https://example.com/1850))
"""


def test_extract_latest_section() -> None:
    section = ec.extract_section(CHANGELOG, "1.0.0-a6")
    assert section.startswith("### Features")
    assert "Add a shiny new thing" in section
    assert "Fix an old thing" in section
    # Must not bleed into the previous version or the intro.
    assert "An older feature" not in section
    assert "confusing header" not in section
    assert "intro prose" not in section
    # The header line itself is omitted from the body.
    assert "## [1.0.0-a6]" not in section


def test_extract_older_section() -> None:
    # The final section runs to the end of the file.
    section = ec.extract_section(CHANGELOG, "1.0.0-a5")
    assert "An older feature" in section
    assert "Add a shiny new thing" not in section


def test_extract_missing_version() -> None:
    with pytest.raises(KeyError, match=r"9\.9\.9"):
        ec.extract_section(CHANGELOG, "9.9.9")


def test_plain_header_without_brackets() -> None:
    # git-cliff can emit headers without the markdown link brackets.
    changelog = "# Changelog\n\n## 1.0.0-a6\n\n* a change\n\n## 1.0.0-a5\n\n* old\n"
    section = ec.extract_section(changelog, "1.0.0-a6")
    assert "a change" in section
    assert "old" not in section


def test_plain_internals_version_header() -> None:
    changelog = (
        "# Changelog\n\n## [1.1](https://x) (2026-06-19)\n\n"
        "* internals change\n\n## [1.0](https://x)\n\n* old\n"
    )
    section = ec.extract_section(changelog, "1.1")
    assert "internals change" in section
    assert "old" not in section


def test_short_version_does_not_prefix_match_longer_one() -> None:
    """``1.0`` must not match a legacy ``1.0.0-aX`` section that may sit below it."""
    changelog = (
        "# Changelog\n\n"
        "## [1.0](https://x) (2026-06-19)\n\n"
        "* the real 1.0 notes\n\n"
        "## [1.0.0-a4](https://x) (2025-01-01)\n\n"
        "* legacy alpha notes\n"
    )
    section = ec.extract_section(changelog, "1.0")
    assert "the real 1.0 notes" in section
    assert "legacy alpha notes" not in section


def test_stable_version_distinct_from_prerelease() -> None:
    """``1.0.0`` must not match a prerelease ``1.0.0-aX`` section that may sit below
    it."""
    changelog = (
        "# Changelog\n\n"
        "## [1.0.0](https://x) (2026-06-20)\n\n"
        "* stable notes\n\n"
        "## [1.0.0-a6](https://x) (2026-06-19)\n\n"
        "* alpha notes\n"
    )
    section = ec.extract_section(changelog, "1.0.0")
    assert "stable notes" in section
    assert "alpha notes" not in section


def test_prerelease_does_not_prefix_match_longer_number() -> None:
    """``1.0.0-a6`` must not match ``1.0.0-a60``."""
    changelog = (
        "# Changelog\n\n"
        "## [1.0.0-a60](https://x)\n\n"
        "* the sixtieth alpha\n\n"
        "## [1.0.0-a6](https://x)\n\n"
        "* the sixth alpha\n"
    )
    section = ec.extract_section(changelog, "1.0.0-a6")
    assert "the sixth alpha" in section
    assert "the sixtieth alpha" not in section
