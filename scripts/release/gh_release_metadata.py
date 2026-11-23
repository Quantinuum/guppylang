"""Choose the GitHub release flags for a package tag.

Takes a ``guppylang-v<version>`` or ``guppylang-internals-v<version>`` tag as a
positional argument and reads the local Git tags in the current repository.
Fetch all release tags before running the script so the comparison is complete.

Writes ``package``, ``version``, ``prerelease``, and ``latest`` to stdout as one
``key=value`` pair per line. The flags are lowercase ``true`` or ``false``.
If ``--github-output <path>`` is given, appends the same lines to that file.

Only the highest stable ``guppylang`` tag can be marked latest. Comparing all
tags also accounts for releases that have not yet been published.
"""

# ruff: noqa: INP001 -- Release scripts are standalone entry points.

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from compute_versions import parse_guppy_version

if TYPE_CHECKING:
    from collections.abc import Iterable


def release_metadata(tag: str, tags: Iterable[str]) -> dict[str, str]:
    """Return the package, version, and release flags for ``tag``.

    Stable internals releases and older stable Guppy releases get neither the
    latest nor the prerelease flag. Alpha, beta, and release candidates for
    either package get the prerelease flag.
    """
    for package in ("guppylang", "guppylang-internals"):
        prefix = f"{package}-v"
        if tag.startswith(prefix):
            version = tag.removeprefix(prefix)
            parsed = parse_guppy_version(version)
            break
    else:
        raise ValueError(f"Not a Guppy package tag: {tag!r}")

    latest = package == "guppylang" and not parsed.is_prerelease
    if latest:
        for other_tag in tags:
            if not other_tag.startswith("guppylang-v"):
                continue
            try:
                other = parse_guppy_version(other_tag.removeprefix("guppylang-v"))
            except ValueError:
                continue
            if not other.is_prerelease and other > parsed:
                latest = False
                break

    return {
        "package": package,
        "version": version,
        "prerelease": str(parsed.is_prerelease).lower(),
        "latest": str(latest).lower(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="Package tag to publish.")
    parser.add_argument("--github-output", help="Append metadata to GITHUB_OUTPUT.")
    args = parser.parse_args(argv)
    tags = subprocess.check_output(
        ["git", "tag", "--list", "guppylang-v*"],  # noqa: S607
        text=True,
    ).splitlines()
    metadata = release_metadata(args.tag, tags)
    output = "".join(f"{key}={value}\n" for key, value in metadata.items())
    print(output, end="")
    if args.github_output:
        with Path(args.github_output).open("a", encoding="utf-8") as file:
            file.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
