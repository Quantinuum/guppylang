"""Tests for the version bump logic in ``scripts/release/compute_versions.py``."""

from __future__ import annotations

from pathlib import Path

import compute_versions as cv
import pytest

POSITIVE_BUMP_TESTS = [
    # auto (best-effort, used when git-cliff cannot refine the bump):
    # a pre-release just increments its number, a stable version bumps patch.
    ("1.0.0-a5", "auto", "1.0.0-a6"),
    ("1.2.3", "auto", "1.2.4"),
    # alpha: increment the alpha number within the same series.
    ("1.0.0-a5", "alpha", "1.0.0-a6"),
    ("1.0.0-a9", "alpha", "1.0.0-a10"),
    # alpha-{patch,minor,major}: start a fresh alpha series off a core bump.
    ("1.2.3", "alpha-patch", "1.2.4-a0"),
    ("1.2.3", "alpha-minor", "1.3.0-a0"),
    ("1.2.3", "alpha-major", "2.0.0-a0"),
    # ... also valid starting from an existing pre-release, regardless of type.
    ("1.2.3-a5", "alpha-patch", "1.2.4-a0"),
    ("1.2.3-rc1", "alpha-minor", "1.3.0-a0"),
    ("1.2.3-b2", "alpha-major", "2.0.0-a0"),
    # beta: promote alpha -> b0, or increment an existing beta series.
    ("1.0.0-a5", "beta", "1.0.0-b0"),
    ("1.0.0-b1", "beta", "1.0.0-b2"),
    # rc: promote alpha/beta -> rc0, or increment an existing rc series.
    ("1.0.0-a5", "rc", "1.0.0-rc0"),
    ("1.0.0-b2", "rc", "1.0.0-rc0"),
    ("1.0.0-rc1", "rc", "1.0.0-rc2"),
    # stable: drop the pre-release suffix.
    ("1.0.0-a5", "stable", "1.0.0"),
    ("1.0.0-rc2", "stable", "1.0.0"),
    # patch/minor/major: plain semver bumps that drop any pre-release.
    ("1.0.1", "patch", "1.0.2"),
    ("1.0.0-a5", "patch", "1.0.1"),
    ("1.2.1", "minor", "1.3.0"),
    ("1.2.1-a5", "minor", "1.3.0"),
    ("1.3.0", "major", "2.0.0"),
    ("1.3.0-a5", "major", "2.0.0"),
]


@pytest.mark.parametrize(("current", "mode", "expected"), POSITIVE_BUMP_TESTS)
def test_bump_guppylang(current: str, mode: str, expected: str) -> None:
    result = cv.bump_guppylang(cv.parse_guppy_version(current), mode)
    assert result.render() == expected


NEGATIVE_BUMP_TESTS = [
    # alpha-bump requires an existing alpha series.
    ("1.0.0", "alpha", "alpha'-bump"),
    ("1.0.0-b1", "alpha", "alpha'-bump"),
    ("1.0.0-rc1", "alpha", "alpha'-bump"),
    # beta-bump requires an alpha or beta series.
    ("1.0.0", "beta", "expected alpha or beta"),
    ("1.0.0-rc1", "beta", "expected alpha or beta"),
    # rc-bump requires a pre-release.
    ("1.0.0", "rc", "non-prerelease"),
    # stable requires a pre-release to drop.
    ("1.0.0", "stable", "already stable"),
]


@pytest.mark.parametrize(("current", "mode", "match"), NEGATIVE_BUMP_TESTS)
def test_bump_guppylang_invalid(current: str, mode: str, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        cv.bump_guppylang(cv.parse_guppy_version(current), mode)


def test_bump_guppylang_unknown_mode() -> None:
    with pytest.raises(ValueError, match="Unknown mode"):
        cv.bump_guppylang(cv.parse_guppy_version("1.0.0"), "wibble-mode")


def test_every_bump_mode_is_exercised() -> None:
    """Guard against a new ``BumpMode`` slipping through untested."""
    expected_positive = {mode for _, mode, _ in POSITIVE_BUMP_TESTS}
    expected_negative = {mode for _, mode, _ in NEGATIVE_BUMP_TESTS}
    expected = expected_negative.union(expected_positive)
    assert {mode.value for mode in cv.BumpMode} == expected


@pytest.mark.parametrize(
    ("current", "bumped_core", "expected"),
    [
        # git-cliff unavailable / no releasable commits -> stay on auto.
        ("1.0.0-a5", None, cv.BumpMode.auto),
        # An unchanged release core is the usual pre-release case -> stay on auto.
        ("1.0.0-a5", (1, 0, 0), cv.BumpMode.auto),
        # A bumped release core maps onto the matching semver bump.
        ("1.2.3", (1, 2, 4), cv.BumpMode.patch),
        ("1.2.3", (1, 3, 0), cv.BumpMode.minor),
        ("1.2.3", (2, 0, 0), cv.BumpMode.major),
        # A lower / equal core never downgrades the bump.
        ("1.2.3", (1, 2, 3), cv.BumpMode.auto),
    ],
)
def test_auto_mode_from_core(
    current: str, bumped_core: tuple[int, int, int] | None, expected: cv.BumpMode
) -> None:
    result = cv._auto_mode_from_core(cv.parse_guppy_version(current), bumped_core)
    assert result is expected


@pytest.mark.parametrize(
    ("current", "bumped_core", "expected"),
    [
        # On a frozen release line, any releasable core change is a patch.
        ("1.2.0", (1, 2, 1), cv.BumpMode.patch),
        ("1.2.0", (1, 3, 0), cv.BumpMode.patch),
        ("1.2.0", (2, 0, 0), cv.BumpMode.patch),
        # No releasable change / no git-cliff -> stay on auto.
        ("1.2.0", (1, 2, 0), cv.BumpMode.auto),
        ("1.2.0", None, cv.BumpMode.auto),
        # A pre-release (e.g. the rc phase) is handled by 'auto' itself.
        ("1.2.0-rc0", (1, 3, 0), cv.BumpMode.auto),
    ],
)
def test_auto_mode_from_core_on_release_line(
    current: str, bumped_core: tuple[int, int, int] | None, expected: cv.BumpMode
) -> None:
    result = cv._auto_mode_from_core(
        cv.parse_guppy_version(current), bumped_core, release_line=True
    )
    assert result is expected


def test_try_resolve_auto_mode_uses_git_cliff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cv, "_git_cliff_bumped_core", lambda root: (1, 3, 0))
    mode = cv.try_resolve_auto_mode(cv.parse_guppy_version("1.2.3"), Path())
    assert mode is cv.BumpMode.minor


def test_try_resolve_auto_mode_release_line_caps_at_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cv, "_git_cliff_bumped_core", lambda root: (1, 3, 0))
    mode = cv.try_resolve_auto_mode(
        cv.parse_guppy_version("1.2.0"), Path(), release_line=True
    )
    assert mode is cv.BumpMode.patch


def test_try_resolve_auto_mode_falls_back_when_git_cliff_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cv, "_git_cliff_bumped_core", lambda root: None)
    mode = cv.try_resolve_auto_mode(cv.parse_guppy_version("1.0.0-a5"), Path())
    assert mode is cv.BumpMode.auto


def test_git_cliff_bumped_core_handles_missing_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*_args: object, **_kwargs: object) -> object:
        raise OSError("git-cliff not found")

    monkeypatch.setattr(cv.subprocess, "run", boom)
    assert cv._git_cliff_bumped_core(Path()) is None


def test_replace_once_requires_single_match() -> None:
    # The file-rewriting helpers refuse to touch a file with no version line,
    # rather than silently producing a no-op. (The happy paths are covered
    # end-to-end in test_release_integration.py.)
    with pytest.raises(ValueError, match="Expected exactly one"):
        cv.set_dunder_version("no version here", "1.0.0")
