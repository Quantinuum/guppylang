"""End-to-end tests driving the release scripts through their CLI entry points."""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

import compute_versions as cv
import extract_changelog as ec
import pytest
import update_changelog as uc

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """A minimal two-package repo laid out like the main guppylang repo."""
    files = {
        "guppylang/pyproject.toml": textwrap.dedent("""\
            [project]
            name = "guppylang"
            version = "1.0.0-a5"
            requires-python = ">=3.10"
            dependencies = [
                "guppylang-internals==1.0.0-a5",
                "numpy>=2.0",
            ]
        """),
        "guppylang/src/guppylang/__init__.py": '__version__ = "1.0.0-a5"\n',
        "guppylang/CHANGELOG.md": "# Changelog\n",
        "guppylang-internals/pyproject.toml": textwrap.dedent("""\
            [project]
            name = "guppylang-internals"
            version = "1.0.0-a5"
            requires-python = ">=3.10"
        """),
        "guppylang-internals/src/guppylang_internals/__init__.py": (
            '__version__ = "1.0.0-a5"\n'
        ),
        "guppylang-internals/CHANGELOG.md": "# Changelog\n",
    }
    repo = tmp_path / "repo"
    for rel, content in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return repo


def _outputs(path: Path) -> dict[str, str]:
    """Parse a ``key=value`` ``GITHUB_OUTPUT`` file into a dict."""
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep:
            values[key] = value
    return values


def test_compute_writes_github_output(fake_repo: Path, tmp_path: Path) -> None:
    out = tmp_path / "gh_output"
    rc = cv.main(
        [
            "--repo-root",
            str(fake_repo),
            "compute",
            "--bump",
            "rc",
            "--github-output",
            str(out),
        ]
    )
    assert rc == 0
    values = _outputs(out)
    assert values["bump_mode"] == "rc"
    assert values["current"] == "1.0.0-a5"
    # Both packages always share the exact same version.
    assert values["version"] == "1.0.0-rc0"


def test_compute_auto_falls_back_without_git_cliff(
    fake_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cv, "_git_cliff_bumped_core", lambda root: None)
    out = tmp_path / "gh_output"
    rc = cv.main(
        ["--repo-root", str(fake_repo), "compute", "--github-output", str(out)]
    )
    assert rc == 0
    values = _outputs(out)
    assert values["bump_mode"] == "auto"
    # Best-effort on a pre-release just increments the alpha number.
    assert values["version"] == "1.0.0-a6"


def test_compute_auto_does_not_resolve_via_git_cliff_if_prerelease(
    fake_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Start from a pre-release version.
    assert cv.main(["--repo-root", str(fake_repo), "set-guppylang", "1.0.0-a7"]) == 0

    monkeypatch.setattr(cv, "_git_cliff_bumped_core", lambda root: (1, 1, 0))
    out = tmp_path / "gh_output"
    rc = cv.main(
        ["--repo-root", str(fake_repo), "compute", "--github-output", str(out)]
    )
    assert rc == 0
    values = _outputs(out)
    assert values["bump_mode"] == "auto"  # Left as auto because we are in a prerelease
    assert values["version"] == "1.0.0-a8"  # Alpha bumped in auto mode


def test_compute_auto_resolves_via_git_cliff_if_not_prerelease(
    fake_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Start from a stable version.
    assert cv.main(["--repo-root", str(fake_repo), "set-guppylang", "1.0.0"]) == 0

    # git-cliff proposing a minor core bump flows through to a minor release.
    monkeypatch.setattr(cv, "_git_cliff_bumped_core", lambda root: (1, 1, 0))
    out = tmp_path / "gh_output"
    rc = cv.main(
        ["--repo-root", str(fake_repo), "compute", "--github-output", str(out)]
    )
    assert rc == 0
    values = _outputs(out)
    assert values["bump_mode"] == "minor"
    assert values["version"] == "1.1.0"


def test_compute_release_branch_caps_at_patch(
    fake_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A shipped, stable release line.
    assert cv.main(["--repo-root", str(fake_repo), "set-guppylang", "1.2.0"]) == 0

    # git-cliff proposing a minor bump is capped to a patch on a release branch.
    monkeypatch.setattr(cv, "_git_cliff_bumped_core", lambda root: (1, 3, 0))
    out = tmp_path / "gh_output"
    rc = cv.main(
        [
            "--repo-root",
            str(fake_repo),
            "compute",
            "--release-branch",
            "--github-output",
            str(out),
        ]
    )
    assert rc == 0
    values = _outputs(out)
    assert values["bump_mode"] == "patch"
    assert values["version"] == "1.2.1"


def test_set_commands_rewrite_package_files(fake_repo: Path) -> None:
    # Both packages are set to the exact same version.
    assert cv.main(["--repo-root", str(fake_repo), "set-guppylang", "1.0.0-rc0"]) == 0
    assert cv.main(["--repo-root", str(fake_repo), "set-internals", "1.0.0-rc0"]) == 0
    assert cv.main(["--repo-root", str(fake_repo), "set-pin", "1.0.0-rc0"]) == 0

    guppy_pyproject = (fake_repo / "guppylang/pyproject.toml").read_text()
    guppy_init = (fake_repo / "guppylang/src/guppylang/__init__.py").read_text()
    internals_pyproject = (fake_repo / "guppylang-internals/pyproject.toml").read_text()
    internals_init = (
        fake_repo / "guppylang-internals/src/guppylang_internals/__init__.py"
    ).read_text()

    assert 'version = "1.0.0-rc0"' in guppy_pyproject
    assert '__version__ = "1.0.0-rc0"' in guppy_init
    assert 'version = "1.0.0-rc0"' in internals_pyproject
    assert '__version__ = "1.0.0-rc0"' in internals_init
    # The pin is rewritten without disturbing the other dependencies.
    assert '"guppylang-internals==1.0.0-rc0"' in guppy_pyproject
    assert '"numpy>=2.0"' in guppy_pyproject
    assert "1.0.0-a5" not in guppy_pyproject


def test_release_rehearsal_end_to_end(
    fake_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cv, "_git_cliff_bumped_core", lambda root: None)

    out = tmp_path / "gh_output"
    assert (
        cv.main(
            [
                "--repo-root",
                str(fake_repo),
                "compute",
                "--bump",
                "stable",
                "--github-output",
                str(out),
            ]
        )
        == 0
    )
    values = _outputs(out)
    guppy = values["version"]
    assert guppy == "1.0.0"  # 1.0.0-a5 promoted to stable

    # Apply the computed versions, exactly as the workflow does. Both packages
    # share the same version.
    assert cv.main(["--repo-root", str(fake_repo), "set-internals", guppy]) == 0
    assert cv.main(["--repo-root", str(fake_repo), "set-guppylang", guppy]) == 0
    assert cv.main(["--repo-root", str(fake_repo), "set-pin", guppy]) == 0

    assert 'version = "1.0.0"' in (fake_repo / "guppylang/pyproject.toml").read_text()
    assert (
        '"guppylang-internals==1.0.0"'
        in (fake_repo / "guppylang/pyproject.toml").read_text()
    )

    # Seed a changelog section, then slice it back out for the release notes.
    section = tmp_path / "section.md"
    section.write_text(
        f"## [{guppy}](https://x) (2026-06-22)\n\n### Features\n\n* Shipped it\n"
    )
    changelog = fake_repo / "guppylang/CHANGELOG.md"
    assert uc.main([str(changelog), guppy, str(section)]) == 0
    assert f"## [{guppy}]" in changelog.read_text()

    capsys.readouterr()  # drop output captured so far
    assert ec.main([str(changelog), guppy]) == 0
    notes = capsys.readouterr().out
    assert "Shipped it" in notes
    # The header line is not part of the extracted notes.
    assert f"## [{guppy}]" not in notes


def test_extract_changelog_cli_missing_version(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\n## [1.0.0](https://x)\n\n* notes\n")
    assert ec.main([str(changelog), "9.9.9"]) == 1
    assert "9.9.9" in capsys.readouterr().err


def test_update_changelog_cli_rejects_empty_section(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n")
    section = tmp_path / "section.md"
    section.write_text("\n")
    assert uc.main([str(changelog), "1.0.0", str(section)]) == 1
    # The changelog is left untouched on failure.
    assert changelog.read_text() == "# Changelog\n"
