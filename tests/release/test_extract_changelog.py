"""Tests for ``scripts/release/extract_changelog.py``."""

from __future__ import annotations

import extract_changelog as ec
import pytest

CHANGELOG = """\
# Changelog

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
    assert "intro prose" not in section
    assert "## [1.0.0-a6]" not in section


def test_extract_older_section() -> None:
    section = ec.extract_section(CHANGELOG, "1.0.0-a5")
    assert "An older feature" in section
    assert "Add a shiny new thing" not in section


def test_extract_with_header() -> None:
    section = ec.extract_section(CHANGELOG, "1.0.0-a6", include_header=True)
    assert section.startswith("## [1.0.0-a6]")


def test_extract_missing_version() -> None:
    with pytest.raises(KeyError):
        ec.extract_section(CHANGELOG, "9.9.9")


def test_plain_internals_version_header() -> None:
    changelog = (
        "# Changelog\n\n## [1.1](https://x) (2026-06-19)\n\n"
        "* internals change\n\n## [1.0](https://x)\n\n* old\n"
    )
    section = ec.extract_section(changelog, "1.1")
    assert "internals change" in section
    assert "old" not in section
