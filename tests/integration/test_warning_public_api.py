import warnings
from dataclasses import dataclass
from types import SimpleNamespace
from typing import ClassVar

import pytest
from guppylang import rich_warnings
from guppylang.defs import GuppyDefinition, GuppyLibrary
from guppylang_internals.definition.common import DefId, Definition
from guppylang_internals.diagnostic import Error, Warning
from guppylang_internals.engine import ENGINE
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.error import GuppyError
from guppylang_internals.span import Loc, Span
from guppylang_internals.warning import emit_warning
from tests.util import guppy_warning_records

file = "public_warning_test.py"


@dataclass(frozen=True)
class DummyDefinition(Definition):
    @property
    def description(self) -> str:
        return "definition"


@dataclass(frozen=True)
class PublicApiWarning(Warning):
    title: ClassVar[str] = "Public API warning"
    span_label: ClassVar[str] = "Triggered from a public entrypoint"


@dataclass(frozen=True)
class PublicApiError(Error):
    title: ClassVar[str] = "Public API error"
    span_label: ClassVar[str] = "Triggered from a public entrypoint"


def make_definition() -> GuppyDefinition:
    return GuppyDefinition(DummyDefinition(DefId.fresh(), "dummy", None))


def make_warning() -> PublicApiWarning:
    return PublicApiWarning(Span(Loc(file, 5, 1), Loc(file, 5, 4)))


def make_error() -> PublicApiError:
    return PublicApiError(Span(Loc(file, 8, 1), Loc(file, 8, 4)))


def register_source() -> None:
    DEF_STORE.sources.add_file(file, "line1\nline2\nline3\nline4\nwarn()\nline6\nerr\n")


def install_check_warning(monkeypatch) -> None:
    """Synthesize a warning from the inner engine `check()` implementation."""

    def fake_check(_def_ids, *, reset=True) -> None:
        del reset
        emit_warning(make_warning())

    monkeypatch.setattr(ENGINE, "check", fake_check)


def install_compile_warning(monkeypatch) -> None:
    """Synthesize a warning from the inner engine `_compile()` implementation."""

    def fake_compile(_def_ids, *, reset=True):
        del reset
        emit_warning(make_warning())
        pointer = SimpleNamespace(package=SimpleNamespace(modules=[]))
        return pointer, [None]

    monkeypatch.setattr(ENGINE, "_compile", fake_compile)


@pytest.mark.parametrize(
    ("install_warning", "run_entrypoint"),
    [
        (
            install_check_warning,
            lambda definition: definition.check(),
        ),
        (
            install_compile_warning,
            lambda definition: definition.compile(),
        ),
    ],
)
def test_single_definition_entrypoints_emit_warning(
    monkeypatch, install_warning, run_entrypoint
):
    """Single-definition public entrypoints should flush one warning."""
    definition = make_definition()
    install_warning(monkeypatch)

    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        run_entrypoint(definition)

    guppy_records = guppy_warning_records(records)
    assert len(guppy_records) == 1
    assert guppy_records[0].filename == file


def test_library_compile_emits_warning_once(monkeypatch):
    """`GuppyLibrary.compile()` should coalesce warnings across its subcalls."""
    library = GuppyLibrary([])
    install_check_warning(monkeypatch)

    def fake_compile(_def_ids, *, reset=True):
        del reset
        emit_warning(make_warning())
        return SimpleNamespace(package=SimpleNamespace(modules=[]))

    monkeypatch.setattr(ENGINE, "compile", fake_compile)

    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        library.compile()

    guppy_records = guppy_warning_records(records)
    assert len(guppy_records) == 1


def test_definition_check_discards_warning_on_error(monkeypatch):
    """Top-level failures should suppress buffered warnings instead of leaking them."""
    definition = make_definition()

    def fake_check(_def_ids, *, reset=True) -> None:
        del reset
        emit_warning(make_warning())
        raise GuppyError(make_error())

    monkeypatch.setattr(ENGINE, "check", fake_check)

    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        with pytest.raises(GuppyError):
            definition.check()

    guppy_records = guppy_warning_records(records)
    assert len(guppy_records) == 0


def test_library_compile_rich_warning_emits_stderr_once(monkeypatch, capsys):
    """Rich mode should not duplicate rendered warnings across library subcalls."""
    library = GuppyLibrary([])
    register_source()
    install_check_warning(monkeypatch)

    def fake_compile(_def_ids, *, reset=True):
        del reset
        emit_warning(make_warning())
        return SimpleNamespace(package=SimpleNamespace(modules=[]))

    monkeypatch.setattr(ENGINE, "compile", fake_compile)

    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        with rich_warnings():
            library.compile()

    guppy_records = guppy_warning_records(records)
    assert len(guppy_records) == 1
    err = capsys.readouterr().err
    assert err.count("Warning: Public API warning") == 1
