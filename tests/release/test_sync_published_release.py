"""Tests for syncing a published release back to main."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

import pytest
import sync_published_release as sync

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def release_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a small main checkout with release-tag contents available."""
    tagged = {
        "guppylang/pyproject.toml": (
            '[project]\nname = "guppylang"\nversion = "1.1.2"\n'
            'dependencies = ["guppylang-internals==1.1.2", "numpy>=2"]\n'
        ),
        "guppylang-internals/pyproject.toml": (
            '[project]\nname = "guppylang-internals"\nversion = "1.1.2"\n'
        ),
        "guppylang/CHANGELOG.md": (
            "# Changelog\n\n## [1.1.2](url)\n\n* Guppy fix\n\n"
            "## [1.1.1](url)\n\n* Older\n"
        ),
        "guppylang-internals/CHANGELOG.md": (
            "# Changelog\n\n## [1.1.2](url)\n\n* Internals fix\n\n"
            "## [1.1.1](url)\n\n* Older\n"
        ),
    }
    for path, text in tagged.items():
        local = tmp_path / path
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(text, encoding="utf-8")
    for path in (sync.GUPPYLANG_INIT, sync.INTERNALS_INIT):
        local = tmp_path / path
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text('__version__ = "1.1.2"\n', encoding="utf-8")
    (tmp_path / "uv.lock").write_text(
        'version = 1\n\n[[package]]\nname = "guppylang"\nversion = "1.1.2"\n'
        '\n[[package]]\nname = "guppylang-internals"\nversion = "1.1.2"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sync, "tagged_file", lambda _tag, path: tagged[path])
    return tmp_path


def test_sync_versions_and_changelogs(release_repo: Path) -> None:
    """Sync both changelogs and all local version references when main is behind."""
    for path in (sync.GUPPYLANG_PYPROJECT, sync.INTERNALS_PYPROJECT):
        local = release_repo / path
        local.write_text(local.read_text().replace("1.1.2", "1.1.1"), encoding="utf-8")
    for path in (sync.GUPPYLANG_INIT, sync.INTERNALS_INIT, "uv.lock"):
        local = release_repo / path
        local.write_text(local.read_text().replace("1.1.2", "1.1.1"), encoding="utf-8")
    for package in sync.PACKAGES:
        local = release_repo / package / "CHANGELOG.md"
        local.write_text("# Changelog\n\n## [1.1.1](url)\n\n* Older\n")

    sync.sync("guppylang-v1.1.2")
    assert "* Guppy fix" in (release_repo / "guppylang/CHANGELOG.md").read_text()
    assert (
        "* Internals fix"
        in (release_repo / "guppylang-internals/CHANGELOG.md").read_text()
    )
    assert (
        '"guppylang-internals==1.1.2"'
        in (release_repo / sync.GUPPYLANG_PYPROJECT).read_text()
    )
    assert all(
        package["version"] == "1.1.2"
        for package in tomllib.loads((release_repo / "uv.lock").read_text())["package"]
    )


def test_newer_alpha_keeps_versions_and_orders_changelog(release_repo: Path) -> None:
    """Keep a newer alpha version and insert older release notes just once."""
    local = release_repo / sync.GUPPYLANG_PYPROJECT
    local.write_text(local.read_text().replace("1.1.2", "1.2.0-a0"))
    for package in sync.PACKAGES:
        local = release_repo / package / "CHANGELOG.md"
        local.write_text(
            "# Changelog\n\n## [1.2.0-a0](url)\n\n* New alpha\n\n"
            "## [1.1.1](url)\n\n* Older\n"
        )
    before_lock = (release_repo / "uv.lock").read_text()

    sync.sync("guppylang-v1.1.2")
    for package in sync.PACKAGES:
        changelog = (release_repo / package / "CHANGELOG.md").read_text()
        assert changelog.index("## [1.2.0-a0]") < changelog.index("## [1.1.2]")
        assert changelog.index("## [1.1.2]") < changelog.index("## [1.1.1]")
    assert (release_repo / "uv.lock").read_text() == before_lock
    assert "1.2.0-a0" in local.read_text()

    before = [
        (release_repo / package / "CHANGELOG.md").read_text()
        for package in sync.PACKAGES
    ]
    sync.sync("guppylang-v1.1.2")
    assert before == [
        (release_repo / package / "CHANGELOG.md").read_text()
        for package in sync.PACKAGES
    ]
