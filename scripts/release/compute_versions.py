#!/usr/bin/env python3
"""Version bump logic for the ``guppylang`` and ``guppylang-internals`` releases.

``guppylang`` follows semantic versioning with an alpha pre-release suffix while
the language is unstable (e.g. ``1.0.0-a5``).  ``guppylang-internals`` uses the
custom scheme ``<guppylang-major>.<build>`` (e.g. ``1.0``, ``1.1``, ...).  The
internals build number is incremented on every release and reset to ``0``
whenever the ``guppylang`` major version changes.

The script is intentionally dependency-free (standard library only) so it can be
run directly in CI without installing the project.  It is split into a ``compute``
command (pure, prints the next versions) and several ``set-*`` commands that
write the new versions into the relevant files.  This lets the release workflow
apply each change as its own, appropriately named commit.

Bump modes (``guppylang``), all easily adjustable:

* ``auto``  -> same as ``alpha`` (the current, unstable-phase default).
* ``alpha`` -> ``1.0.0-a5`` becomes ``1.0.0-a6``.
* ``rc``    -> ``1.0.0-a5`` becomes ``1.0.0-rc1``; ``rc1`` becomes ``rc2``.
* ``patch`` -> ``1.0.0-a5`` becomes ``1.0.1-a1``.
* ``minor`` -> ``1.0.0-a5`` becomes ``1.1.0-a1``.
* ``major`` -> ``1.0.0-a5`` becomes ``2.0.0-a1`` (guarded by the release PR).
* ``stable``-> ``1.0.0-a5`` becomes ``1.0.0`` (drops the pre-release).
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# The number the alpha series restarts from after a core (patch/minor/major)
# bump.  Change this single constant to start fresh pre-releases elsewhere.
INITIAL_PRERELEASE_NUM = 1

BUMP_MODES = ("auto", "alpha", "rc", "patch", "minor", "major", "stable")

GUPPYLANG_PYPROJECT = "guppylang/pyproject.toml"
GUPPYLANG_INIT = "guppylang/src/guppylang/__init__.py"
INTERNALS_PYPROJECT = "guppylang-internals/pyproject.toml"
INTERNALS_INIT = "guppylang-internals/src/guppylang_internals/__init__.py"

_GUPPY_RE = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-?(?P<pre_label>a|b|rc)(?P<pre_num>\d+))?$"
)
_INTERNALS_RE = re.compile(r"^(?P<major>\d+)\.(?P<build>\d+)$")

_VERSION_LINE_RE = re.compile(r'(?m)^version = "[^"]*"')
_DUNDER_VERSION_RE = re.compile(r'(?m)^__version__ = "[^"]*"')
_INTERNALS_DEP_RE = re.compile(r'"guppylang-internals[^"]*"')


@dataclass(frozen=True)
class GuppyVersion:
    major: int
    minor: int
    patch: int
    pre_label: str | None = None
    pre_num: int | None = None

    @property
    def is_prerelease(self) -> bool:
        return self.pre_label is not None

    def render(self) -> str:
        core = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre_label is None:
            return core
        return f"{core}-{self.pre_label}{self.pre_num}"


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
        pre_label=pre_label,
        pre_num=int(pre_num) if pre_num is not None else None,
    )


def bump_guppylang(current: GuppyVersion, mode: str) -> GuppyVersion:
    """Compute the next ``guppylang`` version for the given bump mode."""
    if mode == "auto":
        mode = "alpha"

    if mode == "alpha":
        if current.pre_label != "a" or current.pre_num is None:
            msg = (
                f"Cannot 'alpha'-bump {current.render()!r}: expected an alpha "
                "pre-release. Use 'patch'/'minor'/'major' to start a new series."
            )
            raise ValueError(msg)
        return GuppyVersion(
            current.major, current.minor, current.patch, "a", current.pre_num + 1
        )

    if mode == "rc":
        if current.pre_label == "rc" and current.pre_num is not None:
            next_num = current.pre_num + 1
        elif current.pre_label in ("a", "b"):
            next_num = 1
        else:
            msg = f"Cannot 'rc'-bump stable version {current.render()!r}."
            raise ValueError(msg)
        return GuppyVersion(current.major, current.minor, current.patch, "rc", next_num)

    if mode == "stable":
        if not current.is_prerelease:
            msg = (
                f"{current.render()!r} is already stable; use 'patch'/'minor'/'major'."
            )
            raise ValueError(msg)
        return GuppyVersion(current.major, current.minor, current.patch)

    if mode == "patch":
        return GuppyVersion(
            current.major, current.minor, current.patch + 1, "a", INITIAL_PRERELEASE_NUM
        )
    if mode == "minor":
        return GuppyVersion(
            current.major, current.minor + 1, 0, "a", INITIAL_PRERELEASE_NUM
        )
    if mode == "major":
        return GuppyVersion(current.major + 1, 0, 0, "a", INITIAL_PRERELEASE_NUM)

    msg = f"Unknown bump mode: {mode!r} (expected one of {', '.join(BUMP_MODES)})"
    raise ValueError(msg)


def bump_internals(current_text: str, new_guppy_major: int) -> str:
    """Compute the next ``guppylang-internals`` version.

    Increments the build number, resetting it to ``0`` when the ``guppylang``
    major version changes.  Versions that do not yet follow the
    ``<major>.<build>`` scheme (e.g. the legacy ``1.0.0-a5``) are treated as a
    migration and seeded at ``<new-major>.0``.
    """
    match = _INTERNALS_RE.match(current_text.strip())
    if match is None:
        # Migration from the legacy scheme: seed the first build.
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
    new_guppy = bump_guppylang(current, args.bump)
    new_internals = bump_internals(read_current_internals(root), new_guppy.major)
    major_bumped = new_guppy.major > current.major

    lines = [
        f"current_guppylang={current.render()}",
        f"guppylang={new_guppy.render()}",
        f"internals={new_internals}",
        f"major_bumped={'true' if major_bumped else 'false'}",
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
    compute.add_argument("--bump", choices=BUMP_MODES, default="auto")
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
