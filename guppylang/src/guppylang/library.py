from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from guppylang_internals.definition.common import DefId
from guppylang_internals.engine import DEF_STORE, ENGINE
from hugr.package import Package
from typing_extensions import Self

from guppylang.decorator import metadata
from guppylang.defs import GuppyDefinition, _update_generator_metadata

_LINK_NAME_METADATA_KEY = "guppylang.library.annotated_link_name"


__all__ = [
    "LINK_NAME_METADATA_KEY",
    "GuppyLibrary",
    "link_name",
]


@dataclass(frozen=True)
class GuppyLibrary:
    """A collection of Guppy definitions that can be compiled together into a linkable
    unit exposing a public interface. Libraries can be created using static factory
    methods on this class.

    .. code-block:: python
        from guppylang.library import GuppyLibrary

        @guppy
        def foo() -> int:
            return 42
        @guppy
        def bar() -> int:
            return 7

        # Compilable collection containing `foo` and `bar`.
        lib = GuppyLibrary.from_members(foo, bar)
    """

    members: list[DefId]

    def _type_members(self) -> list[DefId]:
        """Any implementations registered for members of this library. Note that the
        list is only guaranteed to be complete after calling `check()` on the library
        members, since auto-generated implementations may be added during checking."""
        members: list[DefId] = []
        for def_id in self.members:
            # TODO automatic member inclusion should be based on the automatic
            # collection when available
            members.extend(DEF_STORE.type_members[def_id].values())

        return members

    def compile(self) -> Package:
        """Compile this collection of definitions into a HUGR package."""
        ENGINE.check(self.members)
        # Check fills _type_members with additional members only available after
        # checking, so we have to call it before compiling (without an engine reset).
        pointer = ENGINE.compile(self.members + self._type_members(), reset=False)
        for mod in pointer.package.modules:
            _update_generator_metadata(mod)
        return pointer.package

    def check(self) -> None:
        """Type-check all contained definitions."""
        ENGINE.check(self.members)
        ENGINE.check(self._type_members(), reset=False)

    @classmethod
    def from_members(cls, *members: GuppyDefinition) -> Self:
        return cls([member.id for member in members])


def link_name(name: str) -> Any:
    """Decorator to attach a link name to a Guppy definition. It must be placed below
    the @guppy decorator.

    .. code-block:: python

        from guppylang import guppy
        from guppylang.library import link_name


        @guppy.declare
        @link_name("my_link_name")
        def main() -> None:
            pass

        main.compile()
    """
    from guppylang.decorator import metadata

    return metadata(_LINK_NAME_METADATA_KEY, name)


def _get_link_name(f: Callable[..., Any]) -> str | None:
    custom_metadata = getattr(f, "__guppy_metadata__", {})
    assert isinstance(custom_metadata, dict)
    return custom_metadata.get(_LINK_NAME_METADATA_KEY, None)
