#!/usr/bin/env python3
"""Extract a single version's section from a ``CHANGELOG.md`` file.

A section starts at a ``## [<version>] ...`` heading and ends just before the next
``## `` heading (or the end of the file). The ``## [...]`` heading line itself is
omitted from the output of this script.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def extract_section(changelog: str, version: str) -> str:
    """Return the changelog body for ``version`` (raises ``KeyError`` if absent)."""
    # Match the version *exactly*: the version must not be followed by another
    # version character, so e.g. ``1.0`` does not prefix-match ``1.0.0-a4``.
    boundary = r"(?![\w.-])"
    header_re = re.compile(r"^## (?!\[?" + re.escape(version) + boundary + r")")
    target_re = re.compile(r"^## \[?" + re.escape(version) + boundary)

    lines = changelog.splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        if target_re.match(line):
            start = index
            break
    if start is None:
        msg = f"No changelog section found for version {version!r}"
        raise KeyError(msg)

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if header_re.match(lines[index]):
            end = index
            break

    body_start = start + 1  # Omit the header line containing the version.
    section = "\n".join(lines[body_start:end]).strip()
    return section


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("changelog", help="Path to the CHANGELOG.md file.")
    parser.add_argument("version", help="The version section to extract.")
    args = parser.parse_args(argv)

    text = Path(args.changelog).read_text(encoding="utf-8")
    try:
        section = extract_section(text, args.version)
    except KeyError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    print(section)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
