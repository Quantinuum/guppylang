#!/usr/bin/env python3
"""Extract a single version's section from a ``CHANGELOG.md`` file.

This is the *only* code path that turns a changelog into release notes.  Both the
release-PR preview and the published GitHub release read their text from here, so
what you see in the PR preview is exactly what gets published.  The committed
``CHANGELOG.md`` is the single source of truth: this script never regenerates or
reformats anything, it only slices out the requested section verbatim.

A section starts at a ``## [<version>] ...`` heading and ends just before the next
``## `` heading (or the end of the file).  By default the ``## [...]`` heading
line itself is omitted, since the GitHub release already shows the version.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def extract_section(
    changelog: str, version: str, *, include_header: bool = False
) -> str:
    """Return the changelog body for ``version`` (raises ``KeyError`` if absent)."""
    header_re = re.compile(r"^## (?!\[?" + re.escape(version) + r"\b)")
    target_re = re.compile(r"^## \[?" + re.escape(version) + r"\b")

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

    body_start = start if include_header else start + 1
    section = "\n".join(lines[body_start:end]).strip()
    return section


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("changelog", help="Path to the CHANGELOG.md file.")
    parser.add_argument("version", help="The version section to extract.")
    parser.add_argument(
        "--include-header",
        action="store_true",
        help="Include the '## [version]' heading line in the output.",
    )
    args = parser.parse_args(argv)

    text = Path(args.changelog).read_text(encoding="utf-8")
    try:
        section = extract_section(
            text, args.version, include_header=args.include_header
        )
    except KeyError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    print(section)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
