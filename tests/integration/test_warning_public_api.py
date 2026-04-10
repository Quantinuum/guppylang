import warnings
from dataclasses import dataclass
from types import SimpleNamespace
from typing import ClassVar

from guppylang import GuppyWarning
from guppylang.defs import GuppyDefinition, GuppyLibrary
from guppylang_internals.definition.common import DefId, Definition
from guppylang_internals.diagnostic import Warning
from guppylang_internals.engine import ENGINE
from guppylang_internals.error import emit_warning
from guppylang_internals.span import Loc, Span

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


def make_definition() -> GuppyDefinition:
    return GuppyDefinition(DummyDefinition(DefId.fresh(), "dummy", None))


def make_warning() -> PublicApiWarning:
    return PublicApiWarning(Span(Loc(file, 5, 1), Loc(file, 5, 4)))


def test_definition_check_emits_warning(monkeypatch):
    definition = make_definition()

    def fake_check(_def_ids, *, reset=True) -> None:
        del reset
        emit_warning(make_warning())

    monkeypatch.setattr(ENGINE, "check", fake_check)

    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        definition.check()

    assert len(records) == 1
    assert records[0].category is GuppyWarning
    assert records[0].filename == file


def test_definition_compile_emits_warning(monkeypatch):
    definition = make_definition()

    def fake_compile(_def_ids, *, reset=True):
        del reset
        emit_warning(make_warning())
        pointer = SimpleNamespace(package=SimpleNamespace(modules=[]))
        return pointer, [None]

    monkeypatch.setattr(ENGINE, "_compile", fake_compile)

    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        definition.compile()

    assert len(records) == 1
    assert records[0].category is GuppyWarning
    assert records[0].filename == file


def test_library_check_emits_warning_once(monkeypatch):
    library = GuppyLibrary([])

    def fake_check(_def_ids, *, reset=True) -> None:
        del reset
        emit_warning(make_warning())

    monkeypatch.setattr(ENGINE, "check", fake_check)

    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        library.check()

    assert len(records) == 1


def test_library_compile_emits_warning_once(monkeypatch):
    library = GuppyLibrary([])

    def fake_check(_def_ids, *, reset=True) -> None:
        del reset
        emit_warning(make_warning())

    def fake_compile(_def_ids, *, reset=True):
        del reset
        emit_warning(make_warning())
        return SimpleNamespace(package=SimpleNamespace(modules=[]))

    monkeypatch.setattr(ENGINE, "check", fake_check)
    monkeypatch.setattr(ENGINE, "compile", fake_compile)

    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        library.compile()

    assert len(records) == 1
