from __future__ import annotations

from typing import TYPE_CHECKING, Self, no_type_check

from guppylang.decorator import guppy
from guppylang.std.array import array
from guppylang.std.mem import with_owned
from guppylang.std.option import Option, nothing, some
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

    The public API supports ``int`` and non-NaN ``float`` keys. Float infinities are
    valid and ``-0.0`` and ``0.0`` designate the same key. Keys are stored in a 2-3-4
    tree, so lookup, insertion, and removal are logarithmic in the number of entries.
    Values may be linear; use :meth:`discard_empty` after removing or iterating over
    all entries.
    """

    _nodes: array[_Node[K, V], MAX_SIZE]
    _free_nodes: array[int, MAX_SIZE]
    _free_count: int
    _root: int
    _size: int
    _pending: Option[tuple[K, V]]
    _query: Option[K]

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
        self._pending.unwrap_nothing()
        self._query.unwrap_nothing()
        for node in self._nodes:
            node.discard_empty()

    @guppy
    @no_type_check
    def contains_key[K: _Ord, V, MAX_SIZE: nat](
        self: BTreeMap[K, V, MAX_SIZE], key: K
    ) -> bool:
        """Returns whether the map contains ``key``."""
        _validate_key(key)
        self._query.swap(some(key)).unwrap_nothing()
        return with_owned(self, _contains_key)

    @guppy
    @no_type_check
    def get[K: _Ord, V, MAX_SIZE: nat](
        self: BTreeMap[K, V, MAX_SIZE], key: K
    ) -> Option[V]:
        """Returns a copy of the value stored for ``key``, if present."""
        _validate_key(key)
        self._query.swap(some(key)).unwrap_nothing()
        return with_owned(self, _get)

    @guppy
    @no_type_check
    def insert[K: _Ord, V, MAX_SIZE: nat](
        self: BTreeMap[K, V, MAX_SIZE], key: K, value: V @ owned
    ) -> Option[V]:
        """Stores ``value`` for ``key`` and returns a displaced value, if any."""
        _validate_key(key)
        self._pending.swap(some((key, value))).unwrap_nothing()
        return with_owned(self, _insert_pending)


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
def _validate_key[K: _Ord](key: K) -> None:
    if not key.__eq__(key):
        panic("BTreeMap: key must be reflexive")


@guppy
@no_type_check
def _find_owned[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE] @ owned, key: K
) -> tuple[Option[tuple[int, int]], BTreeMap[K, V, MAX_SIZE]]:
    node_i = btree_map._root
    while node_i >= 0:
        node = btree_map._nodes.take(node_i)
        entry_i = _node_entry_index(node, key)
        found = entry_i < node._size and key.__eq__(_node_key(node, entry_i))
        is_leaf = node._leaf
        next_i = -1
        if not is_leaf:
            next_i = _node_child(node, entry_i)
        btree_map._nodes.put(node, node_i)
        if found:
            return some((node_i, entry_i)), btree_map
        if is_leaf:
            return nothing(), btree_map
        node_i = next_i
    return nothing(), btree_map


@guppy
@no_type_check
def _contains_key[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE] @ owned,
) -> tuple[bool, BTreeMap[K, V, MAX_SIZE]]:
    key = btree_map._query.take().unwrap()
    location, btree_map = _find_owned(btree_map, key)
    return location.is_some(), btree_map


@guppy
@no_type_check
def _get[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE] @ owned,
) -> tuple[Option[V], BTreeMap[K, V, MAX_SIZE]]:
    key = btree_map._query.take().unwrap()
    location, btree_map = _find_owned(btree_map, key)
    if location.is_nothing():
        return nothing(), btree_map
    node_i, entry_i = location.unwrap()
    node = btree_map._nodes.take(node_i)
    value = _node_value(node, entry_i)
    btree_map._nodes.put(node, node_i)
    return some(value), btree_map


@guppy
@no_type_check
def _node_entry_index[K: _Ord, V](node: _Node[K, V], key: K) -> int:
    entry_i = 0
    while entry_i < node._size:
        stored_key = _node_key(node, entry_i)
        if key.__lt__(stored_key) or key.__eq__(stored_key):
            break
        entry_i += 1
    return entry_i


@guppy
@no_type_check
def _node_key[K: _Ord, V](node: _Node[K, V], entry_i: int) -> K:
    key, _value = node._entries[entry_i].unwrap()
    return key


@guppy
@no_type_check
def _node_value[K: _Ord, V](node: _Node[K, V], entry_i: int) -> V:
    _key, value = node._entries[entry_i].unwrap()
    return value


@guppy
@no_type_check
def _node_child[K, V](node: _Node[K, V], child_i: int) -> int:
    return node._children[child_i].unwrap()


@guppy
@no_type_check
def _insert_pending[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE] @ owned,
) -> tuple[Option[V], BTreeMap[K, V, MAX_SIZE]]:
    key, value = btree_map._pending.take().unwrap()
    location, btree_map = _find_owned(btree_map, key)
    if location.is_some():
        node_i, entry_i = location.unwrap()
        node = btree_map._nodes.take(node_i)
        stored_key, old_value = node._entries[entry_i].take().unwrap()
        node._entries[entry_i].swap(some((stored_key, value))).unwrap_nothing()
        btree_map._nodes.put(node, node_i)
        return some(old_value), btree_map
    if btree_map._size >= MAX_SIZE:
        panic("BTreeMap.insert: max size reached")
    if btree_map._root < 0:
        root_i, btree_map = _allocate_node(btree_map)
        root = btree_map._nodes.take(root_i)
        root._entries[0].swap(some((key, value))).unwrap_nothing()
        root._size = 1
        btree_map._nodes.put(root, root_i)
        btree_map._root = root_i
        btree_map._size = 1
        return nothing(), btree_map

    root_i = btree_map._root
    root = btree_map._nodes.take(root_i)
    root_is_full = root._size == 3
    btree_map._nodes.put(root, root_i)
    if root_is_full:
        new_root_i, btree_map = _allocate_node(btree_map)
        new_root = btree_map._nodes.take(new_root_i)
        new_root._leaf = False
        new_root._children[0].swap(some(root_i)).unwrap_nothing()
        btree_map._nodes.put(new_root, new_root_i)
        btree_map._root = new_root_i
        btree_map = _split_child(btree_map, new_root_i, 0)

    node_i = btree_map._root
    is_leaf = False
    while not is_leaf:
        node = btree_map._nodes.take(node_i)
        is_leaf = node._leaf
        child_i = 0
        next_i = -1
        if not is_leaf:
            child_i = _node_entry_index(node, key)
            next_i = _node_child(node, child_i)
        btree_map._nodes.put(node, node_i)
        if is_leaf:
            break
        child = btree_map._nodes.take(next_i)
        child_is_full = child._size == 3
        btree_map._nodes.put(child, next_i)
        if child_is_full:
            btree_map = _split_child(btree_map, node_i, child_i)
            node = btree_map._nodes.take(node_i)
            split_key = _node_key(node, child_i)
            if key.__lt__(split_key):
                next_i = _node_child(node, child_i)
            else:
                next_i = _node_child(node, child_i + 1)
            btree_map._nodes.put(node, node_i)
        node_i = next_i

    node = btree_map._nodes.take(node_i)
    entry_i = node._size
    while entry_i > 0:
        if _node_key(node, entry_i - 1).__lt__(key):
            break
        entry = node._entries[entry_i - 1].take().unwrap()
        node._entries[entry_i].swap(some(entry)).unwrap_nothing()
        entry_i -= 1
    node._entries[entry_i].swap(some((key, value))).unwrap_nothing()
    node._size += 1
    btree_map._nodes.put(node, node_i)
    btree_map._size += 1
    return nothing(), btree_map


@guppy
@no_type_check
def _allocate_node[K, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE] @ owned,
) -> tuple[int, BTreeMap[K, V, MAX_SIZE]]:
    if btree_map._free_count <= 0:
        panic("BTreeMap: node pool exhausted")
    btree_map._free_count -= 1
    return btree_map._free_nodes[btree_map._free_count], btree_map


@guppy
@no_type_check
def _split_child[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE] @ owned, parent_i: int, child_i: int
) -> BTreeMap[K, V, MAX_SIZE]:
    parent = btree_map._nodes.take(parent_i)
    old_child_i = parent._children[child_i].unwrap()
    child = btree_map._nodes.take(old_child_i)
    sibling_i, btree_map = _allocate_node(btree_map)
    sibling = btree_map._nodes.take(sibling_i)

    sibling._leaf = child._leaf
    sibling._entries[0].swap(some(child._entries[2].take().unwrap())).unwrap_nothing()
    sibling._size = 1
    child._size = 1
    if not child._leaf:
        sibling._children[0].swap(
            some(child._children[2].take().unwrap())
        ).unwrap_nothing()
        sibling._children[1].swap(
            some(child._children[3].take().unwrap())
        ).unwrap_nothing()

    parent_entry_i = parent._size
    while parent_entry_i > child_i:
        entry = parent._entries[parent_entry_i - 1].take().unwrap()
        parent._entries[parent_entry_i].swap(some(entry)).unwrap_nothing()
        parent_entry_i -= 1
    parent._entries[child_i].swap(
        some(child._entries[1].take().unwrap())
    ).unwrap_nothing()
    child_entry_i = parent._size + 1
    while child_entry_i > child_i + 1:
        child_ref = parent._children[child_entry_i - 1].take().unwrap()
        parent._children[child_entry_i].swap(some(child_ref)).unwrap_nothing()
        child_entry_i -= 1
    parent._children[child_i + 1].swap(some(sibling_i)).unwrap_nothing()
    parent._size += 1

    btree_map._nodes.put(parent, parent_i)
    btree_map._nodes.put(child, old_child_i)
    btree_map._nodes.put(sibling, sibling_i)
    return btree_map


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
        nothing[tuple[K, V]](),
        nothing[K](),
    )
