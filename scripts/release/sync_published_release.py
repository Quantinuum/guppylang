"""Copy a published release's metadata from its tag onto main.

Only the tagged changelog sections and, when the release is newer than main,
the two local package versions are copied. Other dependency changes on main
are left alone.
"""

# ruff: noqa: INP001 -- Release scripts are standalone entry points.

from __future__ import annotations

import argparse
import re
import subprocess
import tomllib
from pathlib import Path

from compute_versions import (
    GUPPYLANG_INIT,
    GUPPYLANG_PYPROJECT,
    INTERNALS_INIT,
    INTERNALS_PYPROJECT,
    parse_guppy_version,
    set_dunder_version,
    set_internals_pin,
    set_version_in_pyproject,
)
from update_changelog import section_for_version, update_changelog

PACKAGES = ("guppylang", "guppylang-internals")


def tagged_file(tag: str, path: str) -> str:
    """Read a file as committed at the release tag."""
    return subprocess.check_output(  # noqa: S603
        ["git", "show", f"{tag}:{path}"],  # noqa: S607
        text=True,
    )


def copy_changelog_section(package: str, version: str, section: str) -> None:
    """Insert a tagged changelog section in order, preserving existing text."""
    path = Path(package) / "CHANGELOG.md"
    changelog = path.read_text(encoding="utf-8")
    updated = update_changelog(changelog, version, section, preserve_existing=True)
    if updated == changelog:
        print(f"{path}: {version} already present; preserving it")
        return
    path.write_text(updated, encoding="utf-8")
    print(f"{path}: copied {version}")


def set_lock_versions(version: str) -> None:
    """Update only the local Guppy package versions in ``uv.lock``."""
    path = Path("uv.lock")
    content = path.read_text(encoding="utf-8")
    for package in PACKAGES:
        pattern = re.compile(
            rf'(?m)(^\[\[package\]\]\nname = "{package}"\nversion = ")[^"]+("\n)'
        )
        content, count = pattern.subn(
            lambda m: m.group(1) + version + m.group(2), content
        )
        if count != 1:
            raise ValueError(f"Expected exactly one local {package} entry in uv.lock")
    # Validate the edited lockfile before writing it.
    tomllib.loads(content)
    path.write_text(content, encoding="utf-8")


def sync(tag: str) -> None:
    """Sync tagged changelogs and advance main's package metadata if needed."""
    tag_pattern = r"guppylang-v[0-9]+\.[0-9]+\.[0-9]+(?:-(?:a|b|rc)[0-9]+)?"
    if not re.fullmatch(tag_pattern, tag):
        raise ValueError(f"Not a guppylang release tag: {tag!r}")
    version = tag.removeprefix("guppylang-v")
    for package in PACKAGES:
        tagged_version = tomllib.loads(tagged_file(tag, f"{package}/pyproject.toml"))[
            "project"
        ]["version"]
        if tagged_version != version:
            raise ValueError(
                f"{tag}: {package} has version {tagged_version}, expected {version}"
            )

    # Validate both source sections before changing any local file.
    sections = {}
    for package in PACKAGES:
        source = tagged_file(tag, f"{package}/CHANGELOG.md")
        section = section_for_version(source, version)
        if section is None:
            raise ValueError(f"{tag}: {package}/CHANGELOG.md has no {version} section")
        sections[package] = section

    current = tomllib.loads(Path(GUPPYLANG_PYPROJECT).read_text(encoding="utf-8"))[
        "project"
    ]["version"]
    for package in PACKAGES:
        copy_changelog_section(package, version, sections[package])

    if parse_guppy_version(current) >= parse_guppy_version(version):
        print(f"main is at {current}; keeping its version and lockfile")
        return

    for pyproject, init in (
        (GUPPYLANG_PYPROJECT, GUPPYLANG_INIT),
        (INTERNALS_PYPROJECT, INTERNALS_INIT),
    ):
        path = Path(pyproject)
        path.write_text(
            set_version_in_pyproject(path.read_text(encoding="utf-8"), version),
            encoding="utf-8",
        )
        path = Path(init)
        path.write_text(
            set_dunder_version(path.read_text(encoding="utf-8"), version),
            encoding="utf-8",
        )
    path = Path(GUPPYLANG_PYPROJECT)
    path.write_text(
        set_internals_pin(path.read_text(encoding="utf-8"), version),
        encoding="utf-8",
    )
    set_lock_versions(version)
    print(f"Updated both package versions, the internals pin, and uv.lock to {version}")


def main() -> None:
    """Parse the release tag and run the sync from the repository root."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="Published guppylang-v<version> release tag")
    args = parser.parse_args()
    sync(args.tag)


if __name__ == "__main__":
    main()
