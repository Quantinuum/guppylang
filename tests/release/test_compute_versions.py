"""Tests for the version bump logic in ``scripts/release/compute_versions.py``."""

from __future__ import annotations

import compute_versions as cv
import pytest


@pytest.mark.parametrize(
    ("current", "mode", "expected"),
    [
        ("1.0.0-a5", "auto", "1.0.0-a6"),
        ("1.0.0-a5", "alpha", "1.0.0-a6"),
        ("1.0.0-a9", "alpha", "1.0.0-a10"),
        ("1.0.0-a5", "rc", "1.0.0-rc1"),
        ("1.0.0-rc1", "rc", "1.0.0-rc2"),
        ("1.0.0-a5", "stable", "1.0.0"),
        ("1.0.0-rc2", "stable", "1.0.0"),
        ("1.0.0-a5", "patch", "1.0.1-a1"),
        ("1.0.0-a5", "minor", "1.1.0-a1"),
        ("1.0.0-a5", "major", "2.0.0-a1"),
    ],
)
def test_bump_guppylang(current: str, mode: str, expected: str) -> None:
    result = cv.bump_guppylang(cv.parse_guppy_version(current), mode)
    assert result.render() == expected


@pytest.mark.parametrize(
    ("current", "mode", "match"),
    [
        ("1.0.0", "alpha", "alpha'-bump"),
        ("1.0.0", "rc", "rc'-bump stable"),
        ("1.0.0", "stable", "already stable"),
    ],
)
def test_bump_guppylang_invalid(current: str, mode: str, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        cv.bump_guppylang(cv.parse_guppy_version(current), mode)


def test_major_bumped_detection() -> None:
    current = cv.parse_guppy_version("1.0.0-a5")
    assert cv.bump_guppylang(current, "major").major > current.major
    assert cv.bump_guppylang(current, "minor").major == current.major


@pytest.mark.parametrize(
    ("current_internals", "new_major", "expected"),
    [
        # Migration from the legacy 3-part scheme.
        ("1.0.0-a5", 1, "1.0"),
        # Normal build increment within the same major.
        ("1.0", 1, "1.1"),
        ("1.7", 1, "1.8"),
        # Reset to build 0 on a major bump.
        ("1.7", 2, "2.0"),
    ],
)
def test_bump_internals(current_internals: str, new_major: int, expected: str) -> None:
    assert cv.bump_internals(current_internals, new_major) == expected


def test_set_version_in_pyproject() -> None:
    text = 'name = "guppylang"\nversion = "1.0.0-a5"\nrequires-python = ">=3.10"\n'
    out = cv.set_version_in_pyproject(text, "1.0.0-a6")
    assert 'version = "1.0.0-a6"' in out
    assert "1.0.0-a5" not in out


def test_set_dunder_version() -> None:
    text = '# comment\n__version__ = "1.0.0-a5"\n'
    out = cv.set_dunder_version(text, "1.0.0-a6")
    assert out == '# comment\n__version__ = "1.0.0-a6"\n'


def test_set_internals_pin() -> None:
    text = (
        'dependencies = [\n    "guppylang-internals~=1.0.0-a5",\n    "numpy~=2.0",\n]\n'
    )
    out = cv.set_internals_pin(text, "1.0")
    assert '"guppylang-internals==1.0"' in out
    assert "~=1.0.0-a5" not in out
    assert '"numpy~=2.0"' in out


def test_replace_once_requires_single_match() -> None:
    with pytest.raises(ValueError, match="Expected exactly one"):
        cv.set_dunder_version("no version here", "1.0.0")
