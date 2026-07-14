import argparse
from contextlib import contextmanager
from pathlib import Path

import pytest
from guppylang.experimental import (
    disable_experimental_features,
    enable_experimental_features,
)

# guppylang.enable_experimental_features()


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

    parser.addoption(
        "--test-exported-hugrs",
        action="store_true",
        default=False,
        help="Validate hugrs exported via --export-test-cases",
    )

    parser.addoption(
        "--target-platform",
        choices=("helios", "sol"),
        default="helios",
        help="Target qsystem platform for integration emulation tests",
    )


@contextmanager
def experimental_features_enabled():
    """Enable experimental features and yield"""
    enable_experimental_features()
    yield
    disable_experimental_features()


@pytest.fixture
def use_experimental_features():
    """Fixture for enabling experimental features."""
    with experimental_features_enabled():
        yield
