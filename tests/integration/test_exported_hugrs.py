import pytest
from tket.passes import NormalizeGuppy
from hugr.package import Package
from pathlib import Path

normalize = NormalizeGuppy()


@pytest.mark.test_exported_hugrs
def test_validate_normalize_exported_hugr(validate, exported_hugr: Path) -> None:
    with Path.open(
        exported_hugr,
        "rb",
    ) as hugr_file:
        pkg = Package.from_bytes(hugr_file.read())

        validate(pkg)
        normalize(pkg.modules[0])
