from hugr import Hugr
from hugr.package import Package, PackagePointer

from pathlib import Path
import pytest
from typing import Any, Literal, cast
from typing_extensions import assert_never

from selene_hugr_qis_compiler import check_hugr

from guppylang.defs import GuppyDefinition
from guppylang.emulator import Platform
from guppylang.std.num import nat

# Keep this in sync with the execution fixtures below. The PR workflow uses the
# auto-applied ``execution`` marker to rerun only emulator-backed integration
# tests against non-default platforms, without also rerunning validation-only
# integration tests.
_EXECUTION_FIXTURES = frozenset({"run_int_fn", "run_nat_fn", "run_float_fn_approx"})


def pytest_generate_tests(metafunc):
    if "exported_hugr" in metafunc.fixturenames:
        exported_hugrs = list(
            Path(__file__)
            .parent.parent.parent.resolve()
            .rglob("tests.integration*.hugr")
        )
        metafunc.parametrize(
            "exported_hugr",
            exported_hugrs,
            ids=lambda p: f"{p.suffixes[-2]}" if len(p.suffixes) >= 2 else f"{p.name}",
        )


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    # Mark by fixture dependency so newly added execution tests are picked up
    # automatically by the Sol CI rerun.
    for item in items:
        fixture_names = getattr(item, "fixturenames", ())
        if _EXECUTION_FIXTURES.intersection(fixture_names):
            item.add_marker("execution")


@pytest.fixture(scope="session")
def export_test_cases_dir(request):
    r = request.config.getoption("--export-test-cases")
    if r is not None:
        if not r.exists():
            r.mkdir(parents=True, exist_ok=True)
        return Path(r).absolute()


@pytest.fixture
def wasm_file(request) -> str:
    test_dir = Path(request.fspath).parents[1]
    return test_dir / Path("resources/test.wasm")


@pytest.fixture
def h2_wasm_file(request) -> str:
    test_dir = Path(request.fspath).parents[1]
    return test_dir / Path("resources/test.h2.wasm")


@pytest.fixture
def validate(request, export_test_cases_dir: Path):
    def validate_impl(
        package: Package | PackagePointer | Hugr, name=None, *, export: bool = True
    ):
        if isinstance(package, PackagePointer):
            package = package.package
        if isinstance(package, Hugr):
            package = Package([package])
        # Validate via the json encoding
        package_bytes = package.to_bytes()

        if export_test_cases_dir and export:
            module_name = request.module.__name__
            function_name = request.node.originalname
            file_name = (
                f"{module_name}-{function_name}{f'_{name}' if name else ''}.hugr"
            )
            export_file = export_test_cases_dir / file_name
            export_file.write_bytes(package_bytes)

        check_hugr(package_bytes)

    return validate_impl


@pytest.fixture
def target_platform(request: pytest.FixtureRequest) -> Platform:
    """Platform to use for integration emulation tests."""
    return cast("Platform", request.config.getoption("--target-platform"))


class LLVMException(Exception):
    pass


def _emulate_fn(ty: Literal["int", "nat", "float"], default_platform: Platform):
    """Use selene to emulate a Guppy function."""
    from guppylang.decorator import guppy
    from guppylang.std.builtins import output

    def f(
        f: GuppyDefinition,
        expected: Any,
        num_qubits: int | None = None,
        args: list[Any] | None = None,
        platform: Platform | None = None,
    ):
        resolved_platform = platform or default_platform
        args = args or []

        @guppy.comptime
        def int_entry() -> None:
            o: int = f(*args)
            output("_test_output", o)

        @guppy.comptime
        def nat_entry() -> None:
            o: nat = f(*(nat(arg) for arg in args))
            output("_test_output", o)

        @guppy.comptime
        def flt_entry() -> None:
            o: float = f(*args)
            output("_test_output", o)

        match ty:
            case "int":
                entry = int_entry
            case "nat":
                entry = nat_entry
            case "float":
                entry = flt_entry
            case _:
                assert_never(ty)
        if num_qubits:
            res = (
                entry.emulator(n_qubits=num_qubits, platform=resolved_platform)
                .statevector_sim()
                .with_seed(42)
                .run()
            )
        else:
            res = (
                entry.emulator(0, platform=resolved_platform)
                .coinflip_sim()
                .with_seed(42)
                .run()
            )
        num = next(v for k, v in res[0] if k == "_test_output")
        if num != expected:
            raise LLVMException(
                f"Expected value ({expected}) doesn't match actual value ({num})"
            )

    return f


@pytest.fixture
def run_int_fn(target_platform: Platform):
    """Emulate an integer function using the Guppy emulator."""
    return _emulate_fn(ty="int", default_platform=target_platform)


@pytest.fixture
def run_nat_fn(target_platform: Platform):
    """Emulate an unsigned integer function using the Guppy emulator."""
    return _emulate_fn(ty="nat", default_platform=target_platform)


@pytest.fixture
def run_float_fn_approx(target_platform: Platform):
    """Like run_int_fn, but takes optional additional parameters `rel`, `abs`
    and `nan_ok` as per `pytest.approx`."""
    run_fn = _emulate_fn(ty="float", default_platform=target_platform)

    def run_approx(
        f: GuppyDefinition,
        expected: float,
        num_qubits: int | None = None,
        args: list[Any] | None = None,
        *,
        rel: float | None = None,
        abs: float | None = None,
        nan_ok: bool = False,
    ):
        return run_fn(
            f,
            pytest.approx(expected, rel=rel, abs=abs, nan_ok=nan_ok),
            num_qubits,
            args,
        )

    return run_approx
