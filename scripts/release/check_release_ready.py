"""Stop release publication while a dependency migration is incomplete."""

# Standalone CLI, following the release scripts in this directory.
# ruff: noqa: INP001

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path


def check_release_ready(repo_root: Path) -> str | None:
    """Return the explicit release blocker, if configured in the repository."""
    with (repo_root / "pyproject.toml").open("rb") as file:
        config = tomllib.load(file)
    release = config.get("tool", {}).get("guppylang", {}).get("release", {})
    reason = release.get("blocked-reason")
    if reason is not None and (not isinstance(reason, str) or not reason.strip()):
        raise ValueError("Release blocked-reason must be a nonempty string")
    return reason


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    args = parser.parse_args(argv)
    try:
        reason = check_release_ready(args.repo_root)
    except (OSError, ValueError) as error:
        print(f"Cannot verify release readiness: {error}", file=sys.stderr)
        return 1
    if reason:
        print(f"Release blocked: {reason}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
