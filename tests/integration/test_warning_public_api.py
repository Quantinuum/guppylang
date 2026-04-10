import warnings
from dataclasses import dataclass
from types import SimpleNamespace
from typing import ClassVar

import pytest
from guppylang import GuppyWarning
from guppylang.defs import GuppyDefinition, GuppyLibrary
from guppylang_internals.definition.common import DefId, Definition
from guppylang_internals.diagnostic import Error, Warning
from guppylang_internals.engine import ENGINE
from guppylang_internals.error import GuppyError
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


def test_definition_check_emits_warning(monkeypatch):
    """`GuppyDefinition.check()` inherits warning flushing from `check_single()`.

    The monkeypatch targets the inner `ENGINE.check()` call to keep the real
    `@pretty_errors` wrapper in place while synthesizing a warning producer.
    """
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
    """`GuppyDefinition.compile()` inherits warning flushing from `compile_single()`.

    The monkeypatch targets the inner `ENGINE._compile()` call so the test still
    exercises the real top-level wrapper around `compile_single()`.
    """
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
    """`GuppyLibrary.check()` should not flush separately for engine subcalls.

    Unlike the single-definition helpers, this method needs its own outer
    `diagnostic_report()` because it orchestrates multiple top-level engine calls.
    """
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
    """`GuppyLibrary.compile()` should coalesce flushes across check and compile."""
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

    assert len(records) == 0
