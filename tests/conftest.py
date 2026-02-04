import argparse
import sys
from pathlib import Path

import guppylang

guppylang.enable_experimental_features()


if sys.version_info < (3, 12):
    # Ignore tests that require Python 3.12 syntax
    collect_ignore_glob = ["*_py312.py"]


def pytest_addoption(parser):
    def dir_path(s):
        path = Path(s)
        if not path.exists() or path.is_dir():
            return path
        msg = f"export-test-cases dir:{path} exists and is not a directory"
        raise argparse.ArgumentTypeError(msg)

    parser.addoption(
        "--export-test-cases",
        action="store",
        type=dir_path,
        help="A directory to which to export test cases",
    )

    parser.addoption(
        "--no_validation",
        dest="validation",
        action="store_false",
        help="Disable validation tests (run by default)",
    )
