#!/usr/bin/env python3
"""Version bump logic for the ``guppylang`` and ``guppylang-internals`` releases.

``guppylang`` follows semantic versioning with an optional pre-release suffix if
the language is unstable (e.g. ``1.0.0-a5``).  ``guppylang-internals`` uses the
custom scheme ``<guppylang-major>.<build>`` (e.g. ``1.0``, ``1.1``, ...).  The
internals build number is incremented on every release and reset to ``0``
whenever the ``guppylang`` major version changes.

Bump modes for ``guppylang``:

* ``auto``  -> ask ``git-cliff`` what the conventional commits imply and express
  that in the current pre-release scheme: a breaking/feature/fix bump of the
  release core maps to ``alpha-major``/``alpha-minor``/``alpha-patch``, while an
  unchanged core (the usual pre-release case) just increments the alpha number.
* ``alpha`` -> ``1.0.0-a1`` becomes ``1.0.0-a2``
* ``alpha-patch`` -> ``1.2.3`` becomes ``1.2.4-a0``
* ``alpha-minor`` -> ``1.2.3`` becomes ``1.3.0-a0``
* ``alpha-major`` -> ``1.2.3`` becomes ``2.0.0-a0``
* ``beta``  -> ``1.0.0-a1`` becomes ``1.0.0-b0``; ``b1`` becomes ``b2``
* ``rc``    -> ``1.0.0-X``  becomes ``1.0.0-rc0``; ``rc1`` becomes ``rc2``
* ``stable``-> ``1.0.0-X``  becomes ``1.0.0`` (drops the pre-release)
* ``patch`` -> ``1.0.1``    becomes ``1.0.2``
* ``minor`` -> ``1.2.1``    becomes ``1.3.0``
* ``major`` -> ``1.3.0``    becomes ``2.0.0``
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class BumpMode(str, Enum):
    auto = "auto"
    alpha = "alpha"
    alpha_patch = "alpha-patch"
    alpha_minor = "alpha-minor"
    alpha_major = "alpha-major"
    beta = "beta"
    rc = "rc"
    stable = "stable"
    patch = "patch"
    minor = "minor"
    major = "major"


class PreLabel(str, Enum):
    alpha = "a"
    beta = "b"
    rc = "rc"


GUPPYLANG_PYPROJECT = "guppylang/pyproject.toml"
GUPPYLANG_INIT = "guppylang/src/guppylang/__init__.py"
INTERNALS_PYPROJECT = "guppylang-internals/pyproject.toml"
INTERNALS_INIT = "guppylang-internals/src/guppylang_internals/__init__.py"

# Scoping used to ask git-cliff about the next guppylang version in ``auto`` mode.
GUPPYLANG_TAG_PATTERN = "^guppylang-v"
GUPPYLANG_INCLUDE_PATH = "guppylang/**"
DEFAULT_CLIFF_CONFIG = "cliff.toml"

_GUPPY_RE = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-?(?P<pre_label>a|b|rc)(?P<pre_num>\d+))?$"
)
_INTERNALS_RE = re.compile(r"^(?P<major>\d+)\.(?P<build>\d+)$")

_VERSION_LINE_RE = re.compile(r'(?m)^version = "[^"]*"')
_DUNDER_VERSION_RE = re.compile(r'(?m)^__version__ = "[^"]*"')
_INTERNALS_DEP_RE = re.compile(r'"guppylang-internals[^"]*"')
_CORE_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


@dataclass(frozen=True)
class GuppyVersion:
    major: int
    minor: int
    patch: int
    pre_label: PreLabel | None = None
    pre_num: int | None = None

    @property
    def is_prerelease(self) -> bool:
        return self.pre_label is not None

    def render(self) -> str:
        core = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre_label is None:
            return core
        return f"{core}-{self.pre_label.value}{self.pre_num}"


def parse_guppy_version(text: str) -> GuppyVersion:
    match = _GUPPY_RE.match(text.strip())
    if match is None:
        msg = f"Cannot parse guppylang version: {text!r}"
        raise ValueError(msg)
    pre_label = match.group("pre_label")
    pre_num = match.group("pre_num")
    return GuppyVersion(
        major=int(match.group("major")),
        minor=int(match.group("minor")),
        patch=int(match.group("patch")),
        pre_label=PreLabel(pre_label) if pre_label is not None else None,
        pre_num=int(pre_num) if pre_num is not None else None,
    )


def bump_guppylang(current: GuppyVersion, mode: str) -> GuppyVersion:
    """Compute the next ``guppylang`` version for the given bump mode."""
    match mode:
        # If we remain with auto even after consulting git-cliff earlier, bump on best
        # effort basis.
        case BumpMode.auto:
            if current.is_prerelease:
                return GuppyVersion(
                    current.major,
                    current.minor,
                    current.patch,
                    current.pre_label,
                    current.pre_num + 1,
                )
            else:
                return GuppyVersion(current.major, current.minor, current.patch + 1)

        case BumpMode.alpha:
            if current.pre_label != "a":
                msg = (
                    f"Cannot 'alpha'-bump {current.render()!r}: expected alpha series."
                    "Use 'alpha-{patch,minor,major}' to start a new series."
                )
                raise ValueError(msg)
            return GuppyVersion(
                current.major,
                current.minor,
                current.patch,
                PreLabel.alpha,
                current.pre_num + 1,
            )

        case BumpMode.alpha_patch:
            return GuppyVersion(
                current.major,
                current.minor,
                current.patch + 1,
                PreLabel.alpha,
                pre_num=0,
            )
        case BumpMode.alpha_minor:
            return GuppyVersion(
                current.major, current.minor + 1, 0, PreLabel.alpha, pre_num=0
            )
        case BumpMode.alpha_major:
            return GuppyVersion(current.major + 1, 0, 0, PreLabel.alpha, pre_num=0)

        case BumpMode.beta:
            if current.pre_label == PreLabel.alpha:
                next_num = 0
            elif current.pre_label == PreLabel.beta:
                next_num = current.pre_num + 1
            else:
                msg = (
                    f"Cannot 'beta'-bump {current.render()!r}: expected alpha or beta "
                    "series. Use 'alpha-{patch,minor,major}' to start a new series."
                )
                raise ValueError(msg)
            return GuppyVersion(
                current.major, current.minor, current.patch, PreLabel.beta, next_num
            )

        case BumpMode.rc:
            if current.pre_label in (PreLabel.alpha, PreLabel.beta):
                next_num = 0
            elif current.pre_label == PreLabel.rc:
                next_num = current.pre_num + 1
            else:
                msg = f"Cannot 'rc'-bump non-prerelease version: {current.render()!r}."
                raise ValueError(msg)
            return GuppyVersion(
                current.major, current.minor, current.patch, PreLabel.rc, next_num
            )

        case BumpMode.stable:
            if not current.is_prerelease:
                msg = (
                    f"{current.render()!r} already stable; use 'patch'/'minor'/'major'."
                )
                raise ValueError(msg)
            return GuppyVersion(current.major, current.minor, current.patch)

        case BumpMode.patch:
            return GuppyVersion(current.major, current.minor, current.patch + 1)
        case BumpMode.minor:
            return GuppyVersion(current.major, current.minor + 1, 0)
        case BumpMode.major:
            return GuppyVersion(current.major + 1, 0, 0)

    bump_modes = BumpMode.__members__.values()
    msg = f"Unknown mode: {mode!r} (must be one of {', '.join(bump_modes)})"
    raise ValueError(msg)


def _auto_mode_from_core(
    current: GuppyVersion, bumped_core: tuple[int, int, int] | None
) -> BumpMode:
    if bumped_core is not None:
        major, minor, patch = bumped_core
        if major > current.major:
            return BumpMode.major
        if major == current.major and minor > current.minor:
            return BumpMode.minor
        if (major, minor) == (current.major, current.minor) and patch > current.patch:
            return BumpMode.patch
    return BumpMode.auto


def _git_cliff_bumped_core(root: Path) -> tuple[int, int, int] | None:
    """Return the ``major.minor.patch`` git-cliff proposes for ``guppylang``.

    Returns ``None`` when git-cliff is unavailable or produces no parseable
    version (e.g. when there are no releasable commits).
    """
    cmd = [
        "git-cliff",
        "--config",
        DEFAULT_CLIFF_CONFIG,
        "--include-path",
        GUPPYLANG_INCLUDE_PATH,
        "--tag-pattern",
        GUPPYLANG_TAG_PATTERN,
        "--bumped-version",
    ]
    try:
        result = subprocess.run(  # noqa: S603
            cmd, cwd=str(root), capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.SubprocessError):
        return None
    match = _CORE_RE.search(result.stdout)
    if match is None:
        return None
    return (int(match[1]), int(match[2]), int(match[3]))


def try_resolve_auto_mode(current: GuppyVersion, root: Path) -> BumpMode:
    """Resolve the ``auto`` bump mode by consulting git-cliff, if possible."""
    bumped_core = _git_cliff_bumped_core(root)
    return _auto_mode_from_core(current, bumped_core)


def bump_internals(current_text: str, new_guppy_major: int) -> str:
    """Compute the next ``guppylang-internals`` version.

    Increments the build number, resetting it to ``0`` when the ``guppylang``
    major version changes.  Versions that do not yet follow the
    ``<major>.<build>`` scheme (e.g. the legacy ``1.0.0-a5``) are treated as a
    migration and seeded at ``<new-major>.0``.
    """
    match = _INTERNALS_RE.match(current_text.strip())
    if match is None:
        # Seed the first build of the new series as 0
        return f"{new_guppy_major}.0"
    current_major = int(match.group("major"))
    current_build = int(match.group("build"))
    if current_major != new_guppy_major:
        return f"{new_guppy_major}.0"
    return f"{new_guppy_major}.{current_build + 1}"


def _replace_once(
    pattern: re.Pattern[str], replacement: str, text: str, *, what: str
) -> str:
    new_text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        msg = f"Expected exactly one {what} to replace, found {count}."
        raise ValueError(msg)
    return new_text


def set_version_in_pyproject(text: str, version: str) -> str:
    return _replace_once(
        _VERSION_LINE_RE, f'version = "{version}"', text, what="project version"
    )


def set_dunder_version(text: str, version: str) -> str:
    return _replace_once(
        _DUNDER_VERSION_RE, f'__version__ = "{version}"', text, what="__version__"
    )


def set_internals_pin(text: str, internals_version: str) -> str:
    return _replace_once(
        _INTERNALS_DEP_RE,
        f'"guppylang-internals=={internals_version}"',
        text,
        what="guppylang-internals dependency",
    )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def read_current_guppylang(root: Path) -> GuppyVersion:
    text = _read(root / GUPPYLANG_PYPROJECT)
    match = _VERSION_LINE_RE.search(text)
    if match is None:
        msg = f"No project version found in {GUPPYLANG_PYPROJECT}"
        raise ValueError(msg)
    raw = match.group(0).split('"')[1]
    return parse_guppy_version(raw)


def read_current_internals(root: Path) -> str:
    text = _read(root / INTERNALS_PYPROJECT)
    match = _VERSION_LINE_RE.search(text)
    if match is None:
        msg = f"No project version found in {INTERNALS_PYPROJECT}"
        raise ValueError(msg)
    return match.group(0).split('"')[1]


def cmd_compute(args: argparse.Namespace) -> int:
    root = Path(args.repo_root)
    current = read_current_guppylang(root)
    internals = read_current_internals(root)
    mode = BumpMode(args.bump)
    if mode is BumpMode.auto:
        mode = try_resolve_auto_mode(current, root)
    new_guppy = bump_guppylang(current, mode)
    new_internals = bump_internals(internals, new_guppy.major)

    lines = [
        f"bump_mode={mode.value}",
        f"current_guppylang={current.render()}",
        f"current_internals={internals}",
        f"guppylang={new_guppy.render()}",
        f"internals={new_internals}",
    ]
    print("\n".join(lines))
    if args.github_output is not None:
        with Path(args.github_output).open("a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    return 0


def cmd_set_internals(args: argparse.Namespace) -> int:
    root = Path(args.repo_root)
    pyproject = root / INTERNALS_PYPROJECT
    init = root / INTERNALS_INIT
    _write(pyproject, set_version_in_pyproject(_read(pyproject), args.version))
    _write(init, set_dunder_version(_read(init), args.version))
    return 0


def cmd_set_guppylang(args: argparse.Namespace) -> int:
    root = Path(args.repo_root)
    pyproject = root / GUPPYLANG_PYPROJECT
    init = root / GUPPYLANG_INIT
    _write(pyproject, set_version_in_pyproject(_read(pyproject), args.version))
    _write(init, set_dunder_version(_read(init), args.version))
    return 0


def cmd_set_pin(args: argparse.Namespace) -> int:
    root = Path(args.repo_root)
    pyproject = root / GUPPYLANG_PYPROJECT
    _write(pyproject, set_internals_pin(_read(pyproject), args.version))
    return 0


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=str(_default_repo_root()),
        help="Repository root (defaults to the script's repository).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    compute = sub.add_parser("compute", help="Compute and print the next versions.")
    compute.add_argument(
        "--bump", choices=BumpMode.__members__.values(), default="auto"
    )
    compute.add_argument(
        "--github-output",
        default=None,
        help="Optional path of a GITHUB_OUTPUT file to append the results to.",
    )
    compute.set_defaults(func=cmd_compute)

    set_internals = sub.add_parser(
        "set-internals", help="Write the guppylang-internals version."
    )
    set_internals.add_argument("version")
    set_internals.set_defaults(func=cmd_set_internals)

    set_guppylang = sub.add_parser("set-guppylang", help="Write the guppylang version.")
    set_guppylang.add_argument("version")
    set_guppylang.set_defaults(func=cmd_set_guppylang)

    set_pin = sub.add_parser(
        "set-pin", help="Pin the guppylang-internals dependency in guppylang."
    )
    set_pin.add_argument("version")
    set_pin.set_defaults(func=cmd_set_pin)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
