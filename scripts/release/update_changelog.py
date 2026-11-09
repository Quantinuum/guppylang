#!/usr/bin/env python3
"""Insert a freshly generated section into a ``CHANGELOG.md``.

The release workflow asks git-cliff for a single ``## [<version>] ...`` section
and uses this script to splice it into the package's ``CHANGELOG.md`` in
descending version order, preserving the file's title/intro/front-matter.

The operation is idempotent: if a section for ``version`` already exists (e.g. a
previous draft of the same release), it is removed first and replaced. This is
what lets the workflow regenerate the draft on every push (while the
``X-regen-changelog`` label is set) without piling up duplicate sections.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from compute_versions import parse_guppy_version


def _section_bounds(lines: list[str], version: str) -> tuple[int, int] | None:
    """Return the ``[start, end)`` line range of ``version``'s section, if any."""
    boundary = r"(?![\w.-])"
    target_re = re.compile(r"^## \[?" + re.escape(version) + boundary)
    start: int | None = None
    for index, line in enumerate(lines):
        if target_re.match(line):
            start = index
            break
    if start is None:
        return None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    return start, end


def _first_version_header(lines: list[str]) -> int | None:
    for index, line in enumerate(lines):
        if line.startswith("## ["):
            return index
    return None


def section_for_version(changelog: str, version: str) -> str | None:
    """Return the complete section for ``version``, including its heading."""
    lines = changelog.splitlines()
    bounds = _section_bounds(lines, version)
    if bounds is None:
        return None
    start, end = bounds
    return "\n".join(lines[start:end]).rstrip() + "\n"


def _ordered_insertion(lines: list[str], version: str) -> int:
    """Find where ``version`` belongs among descending version headings."""
    first = _first_version_header(lines)
    try:
        incoming = parse_guppy_version(version)
    except ValueError:
        # Keep the historical prepend behavior for legacy headings such as 1.0.
        return first if first is not None else len(lines)

    found_parseable = False
    for index, line in enumerate(lines):
        match = re.match(r"^## \[([^]]+)\]", line)
        if match is None:
            continue
        try:
            existing = parse_guppy_version(match.group(1))
        except ValueError:
            continue
        found_parseable = True
        if existing < incoming:
            return index
    if not found_parseable:
        return first if first is not None else len(lines)
    return len(lines)


def update_changelog(
    changelog: str,
    version: str,
    section: str,
    *,
    preserve_existing: bool = False,
) -> str:
    """Insert a section into the changelog, following descending version order.

    By default, replace an existing section for ``version`` so the release PR
    can regenerate its draft. If ``preserve_existing`` is ``True``, return the
    changelog unchanged if the version already exists. Either setting inserts
    the section when it is missing.
    """
    lines = changelog.splitlines()
    section_block = section.strip("\n").splitlines()

    # Drop any existing section for this version so regeneration is idempotent.
    existing = _section_bounds(lines, version)
    if existing is not None:
        if preserve_existing:
            return changelog
        start, end = existing
        del lines[start:end]
        insert_at = start
    else:
        insert_at = _ordered_insertion(lines, version)

    # Ensure a blank line separates the new section from following content.
    block = [*section_block, ""]
    new_lines = lines[:insert_at] + block + lines[insert_at:]
    text = "\n".join(new_lines)
    if not text.endswith("\n"):
        text += "\n"
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("changelog", help="Path to the CHANGELOG.md to update.")
    parser.add_argument("version", help="The version of the new section.")
    parser.add_argument(
        "section",
        help="Path to a file containing the rendered '## [version] ...' section.",
    )
    args = parser.parse_args(argv)

    changelog_path = Path(args.changelog)
    section_text = Path(args.section).read_text(encoding="utf-8")
    if not section_text.strip():
        print("error: generated section is empty", file=sys.stderr)
        return 1

    updated = update_changelog(
        changelog_path.read_text(encoding="utf-8"), args.version, section_text
    )
    changelog_path.write_text(updated, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
