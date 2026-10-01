"""Command line interface for `auto-hugr-ext`."""

from __future__ import annotations

import argparse
from pathlib import Path

from auto_hugr_ext.generate import generate_new_hugr_ext
from auto_hugr_ext.python_module import generate_python_module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="auto-hugr-ext")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser(
        "gen", help="Generate an extension JSON file from a source file."
    )
    gen.add_argument("source", type=Path, help="Python file declaring the extension.")
    gen.add_argument("ext_name", help="Name of the extension to generate.")
    gen.add_argument("-o", "--out", type=Path, default=None, help="Output file path.")
    gen.add_argument(
        "--python-out",
        type=Path,
        default=None,
        help="Generated Guppy source path (default: <source>_generated.py).",
    )

    args = parser.parse_args(argv)
    extension = generate_new_hugr_ext(args.source, args.ext_name, args.out)
    json_path = args.out or args.source.with_suffix(".json")
    python_path = args.python_out or args.source.with_name(
        f"{args.source.stem}_generated.py"
    )
    generate_python_module(args.source, json_path, python_path)
    print(f"Generated {extension.name} {extension.version}")  # noqa: T201
    print(f"  extension: {json_path}")  # noqa: T201
    print(f"  source: {python_path}")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
