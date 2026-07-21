from __future__ import annotations

from typing import TYPE_CHECKING, Self, no_type_check

from guppylang.decorator import guppy
from guppylang.std.array import array
from guppylang.std.option import Option, nothing
from guppylang.std.num import nat
from guppylang.std.platform import panic

if TYPE_CHECKING:
    from guppylang.std.lang import owned


@guppy.protocol
class _Ord:
    """Internal structural protocol for keys in :class:`BTreeMap`.

    TODO: Replace this with a public standard-library ordering API once one is designed.
    """

    @guppy.require
    def __lt__(self, other: Self) -> bool: ...

    @guppy.require
    def __eq__(self, other: Self) -> bool: ...


@guppy.struct
class _Node[K, V]:
    """A 2-3-4 tree node.

    TODO: Make this fan-out configurable when Guppy supports type-level arithmetic
    for derived array sizes.
    """

    _entries: array[Option[tuple[K, V]], 3]
    _children: array[Option[int], 4]
    _size: int
    _leaf: bool

    @guppy
    @no_type_check
    def discard_empty[K, V](self: _Node[K, V] @ owned) -> None:
        if self._size != 0:
            panic("BTreeMap._Node.discard_empty: node is not empty")
        for entry in self._entries:
            entry.unwrap_nothing()
        for child in self._children:
            child.unwrap_nothing()


@guppy.struct
class BTreeMap[K, V, MAX_SIZE: nat]:
    """A fixed-capacity ordered map.

    The public API supports ``int`` and non-NaN ``float`` keys. Keys are stored in a
    2-3-4 tree, so lookup, insertion, and removal are logarithmic in the number of
    entries. Values may be linear; use :meth:`discard_empty` after removing or
    iterating over all entries.
    """

    _nodes: array[_Node[K, V], MAX_SIZE]
    _free_nodes: array[int, MAX_SIZE]
    _free_count: int
    _root: int
    _size: int

    @guppy
    @no_type_check
    def __len__(self) -> int:
        """Returns the number of entries in the map."""
        return self._size

    @guppy
    @no_type_check
    def discard_empty[K: _Ord, V, MAX_SIZE: nat](
        self: BTreeMap[K, V, MAX_SIZE] @ owned,
    ) -> None:
        """Discards an empty map containing potentially linear values."""
        if self._size != 0:
            panic("BTreeMap.discard_empty: map is not empty")
        for node in self._nodes:
            node.discard_empty()


@guppy
@no_type_check
def _empty_node[K, V]() -> _Node[K, V]:
    return _Node(
        array(nothing[tuple[K, V]]() for _ in range(3)),
        array(nothing[int]() for _ in range(4)),
        0,
        True,
    )


@guppy
@no_type_check
def empty_btree_map[K: _Ord, V, MAX_SIZE: nat]() -> BTreeMap[K, V, MAX_SIZE]:
    """Constructs an empty fixed-capacity B-tree map."""
    return BTreeMap(
        array(_empty_node[K, V]() for _ in range(MAX_SIZE)),
        array(i for i in range(MAX_SIZE)),
        int(MAX_SIZE),
        -1,
        0,
    )
