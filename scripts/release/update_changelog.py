#!/usr/bin/env python3
"""Insert a freshly generated section into a ``CHANGELOG.md``.

The release workflow asks git-cliff for a single ``## [<version>] ...`` section
and uses this script to splice it into the package's ``CHANGELOG.md`` just above
the most recent existing version, preserving the file's title/intro/front-matter.

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


def update_changelog(changelog: str, version: str, section: str) -> str:
    """Return ``changelog`` with ``section`` inserted/replaced for ``version``."""
    lines = changelog.splitlines()
    section_block = section.strip("\n").splitlines()

    # Drop any existing section for this version so regeneration is idempotent.
    existing = _section_bounds(lines, version)
    if existing is not None:
        start, end = existing
        del lines[start:end]
        insert_at = start
    else:
        first = _first_version_header(lines)
        insert_at = first if first is not None else len(lines)

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
