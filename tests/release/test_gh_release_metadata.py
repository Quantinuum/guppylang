"""Tests for classifying package tags before publishing GitHub releases."""

# ruff: noqa: S603, S607 -- Tests run git in a temporary repository.

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import gh_release_metadata as rm
import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("version", "other_versions", "latest"),
    [
        ("1.0.0", [], True),
        ("1.3.0", ["1.2.9", "1.3.0-rc1", "1.4.0-a0"], True),
        ("1.3.1", ["1.3.0", "1.4.0-rc0"], True),
        ("1.2.10", ["1.3.0"], False),
        ("1.3.1", ["1.3.2"], False),
        ("1.9.9", ["1.10.0"], False),
        ("1.10.0", ["1.9.9", "1.10.0"], True),
        ("1.2.10", ["1.2.9"], True),
        ("1.2.9", ["1.2.10"], False),
        ("1.99.99", ["2.0.0"], False),
    ],
)
def test_stable_guppy_latest(
    version: str, other_versions: list[str], latest: bool
) -> None:
    tags = [f"guppylang-v{other}" for other in other_versions]
    metadata = rm.release_metadata(f"guppylang-v{version}", tags)
    assert metadata == {
        "package": "guppylang",
        "version": version,
        "prerelease": "false",
        "latest": str(latest).lower(),
    }


@pytest.mark.parametrize("package", ["guppylang", "guppylang-internals"])
@pytest.mark.parametrize("version", ["2.0.0-a0", "2.0.0-b1", "2.0.0-rc2", "2.0.0rc3"])
def test_prereleases(package: str, version: str) -> None:
    metadata = rm.release_metadata(f"{package}-v{version}", ["guppylang-v1.0.0"])
    assert metadata["package"] == package
    assert metadata["version"] == version
    assert metadata["prerelease"] == "true"
    assert metadata["latest"] == "false"


def test_stable_internals_gets_neither_label() -> None:
    metadata = rm.release_metadata("guppylang-internals-v2.0.0", [])
    assert metadata["prerelease"] == "false"
    assert metadata["latest"] == "false"


def test_other_packages_and_malformed_tags_do_not_affect_latest() -> None:
    metadata = rm.release_metadata(
        "guppylang-v1.0.0",
        ["guppylang-internals-v9.0.0", "other-v9.0.0", "guppylang-vinvalid"],
    )
    assert metadata["latest"] == "true"


@pytest.mark.parametrize("tag", ["other-v1.0.0", "guppylang-vinvalid"])
def test_invalid_release_tag(tag: str) -> None:
    with pytest.raises(ValueError, match=r"Not a Guppy package tag|Cannot parse"):
        rm.release_metadata(tag, [])


def test_cli_compares_git_tags_and_appends_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init", "-q"], check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-qm",
            "Initial commit",
            "--allow-empty",
        ],
        check=True,
    )
    for tag in ("guppylang-v1.2.10", "guppylang-v1.3.0", "guppylang-v1.4.0-a0"):
        subprocess.run(["git", "tag", tag], check=True)

    output = tmp_path / "output"
    output.write_text("existing=value\n")
    assert rm.main(["guppylang-v1.2.10", "--github-output", str(output)]) == 0
    assert output.read_text() == (
        "existing=value\npackage=guppylang\nversion=1.2.10\n"
        "prerelease=false\nlatest=false\n"
    )
