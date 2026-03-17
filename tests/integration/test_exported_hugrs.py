import pytest
from tket.passes import NormalizeGuppy
from hugr.package import Package
from pathlib import Path

normalize = NormalizeGuppy()

# Find all .hugr files from the root directory
exported_hugrs = list(Path(__file__).parent.parent.parent.resolve().rglob("*.hugr"))


@pytest.mark.parametrize(
    "exported_hugr",
    exported_hugrs,
    ids=lambda p: f"{p.suffixes[-2]}" if len(p.suffixes) >= 2 else f"{p.name}",
)
def test_validate_normalize_exported_hugr(validate, exported_hugr: Path) -> None:
    with Path.open(
        exported_hugr,
        "rb",
    ) as hugr_file:
        pkg = Package.from_bytes(hugr_file.read())

        validate(pkg)
        normalize(pkg.modules[0])
