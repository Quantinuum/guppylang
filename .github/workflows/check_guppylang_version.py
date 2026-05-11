import json
from pathlib import Path

import guppylang


def main() -> None:
    GUPPYLANG_PACKAGE_VERSION = guppylang.__version__

    with Path.open(Path(".release-please-manifest.json")) as json_data:
        release_please_data = json.load(json_data)
        MANIFEST_GUPPYLANG_VERSION = release_please_data["guppylang"]

    assert GUPPYLANG_PACKAGE_VERSION == MANIFEST_GUPPYLANG_VERSION


if __name__ == "__main__":
    main()
