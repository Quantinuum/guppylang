#!/usr/bin/env python3
"""Render the release-notes preview block in a release PR's body.

The preview shows, verbatim, the changelog sections that will be published for
each package -- i.e. the exact output of ``extract_changelog.py``. It lives
between two HTML-comment markers so it can be refreshed in place on every push to
the release branch without disturbing the rest of the PR description.

This script only manipulates text; it never talks to GitHub. The workflow pipes
the current PR body in and the rendered body out.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BEGIN = "<!-- BEGIN RELEASE NOTES PREVIEW -->"
END = "<!-- END RELEASE NOTES PREVIEW -->"


def render_block(packages: list[tuple[str, str, str]]) -> str:
    """Render the preview block for ``(name, version, section)`` triples."""
    parts = [
        BEGIN,
        "## :memo: Release notes preview",
        "",
        "Extracted verbatim from the committed changelogs. This is **exactly** "
        "what will be published to the GitHub releases.",
    ]
    for name, version, section in packages:
        body = section.strip() or "_No changelog entry._"
        parts += [
            "",
            f"<details><summary><code>{name}</code> {version}</summary>",
            "",
            body,
            "",
            "</details>",
        ]
    parts.append(END)
    return "\n".join(parts)


def update_body(body: str, block: str) -> str:
    """Insert or replace the preview block in ``body``."""
    if BEGIN in body and END in body:
        before = body[: body.index(BEGIN)]
        after = body[body.index(END) + len(END) :]
        return f"{before.rstrip()}\n\n{block}\n{after.lstrip()}".rstrip() + "\n"
    return f"{body.rstrip()}\n\n{block}\n"


def _read(path: str | None) -> str:
    if path in (None, "-"):
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--body", default="-", help="Current PR body file ('-' = stdin)."
    )
    parser.add_argument(
        "--package",
        action="append",
        default=[],
        nargs=3,
        metavar=("NAME", "VERSION", "SECTION_FILE"),
        help="A package's name, version and the file with its changelog section.",
    )
    args = parser.parse_args(argv)

    packages = [
        (name, version, Path(section_file).read_text(encoding="utf-8"))
        for name, version, section_file in args.package
    ]
    block = render_block(packages)
    sys.stdout.write(update_body(_read(args.body), block))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
