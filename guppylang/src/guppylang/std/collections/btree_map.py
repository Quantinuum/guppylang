from __future__ import annotations

from typing import TYPE_CHECKING, Self, no_type_check

from guppylang.decorator import guppy
from guppylang.std.array import array
from guppylang.std.lang import Copy
from guppylang.std.option import Option, nothing, some
from guppylang.std.num import nat
from guppylang.std.platform import panic

if TYPE_CHECKING:
    from guppylang.std.lang import owned


@guppy.protocol
class _Ord:
    """Internal structural protocol for keys in :class:`BTreeMap`.

    This is deliberately private: public callers are only promised ``int`` and
    non-NaN ``float`` keys. Protocol bounds currently also make a key copyable and
    droppable, which is what permits comparisons while the map retains its key.

    Implementations must make ``__lt__`` and ``__eq__`` describe the same ordering.
    In particular, equal keys must not be ordered, and every accepted key must equal
    itself. The latter is checked at each public operation to reject ``NaN``.

    TODO: Replace this with a public standard-library ordering API once one is designed.
    """

    @guppy.require
    def __lt__(self, other: Self) -> bool: ...

    @guppy.require
    def __eq__(self, other: Self) -> bool: ...


@guppy.struct
class _Node[K, V]:
    """A 2-3-4 tree node.

    Live keys and entries occupy the prefix ``[0, _size)`` in sorted order. Keys
    are deliberately stored separately from their values: comparison can then
    borrow a copyable key without inspecting an entry that may contain a linear
    value. An internal node has exactly ``_size + 1`` live child indices; every
    remaining slot is ``nothing``. This representation lets entries and child
    links be moved without cloning a potentially linear value.

    TODO: Make this fan-out configurable when Guppy supports type-level arithmetic
    for derived array sizes.
    """

    # `_keys[i]` mirrors the key in `_entries[i]`. Keeping this copyable index
    # separate is what makes lookup and rebalancing valid for linear `V`.
    _keys: array[Option[K], 3]
    _entries: array[Option[tuple[K, V]], 3]
    _children: array[Option[int], 4]
    _size: int
    _leaf: bool

    @guppy
    @no_type_check
    def discard_empty[K, V](self: _Node[K, V] @ owned) -> None:
        if self._size != 0:
            panic("BTreeMap._Node.discard_empty: node is not empty")
        for key in self._keys:
            key.unwrap_nothing()
        for entry in self._entries:
            entry.unwrap_nothing()
        for child in self._children:
            child.unwrap_nothing()


@guppy.struct
class BTreeMap[K, V, MAX_SIZE: nat]:
    """A fixed-capacity ordered map.

    The public API supports ``int`` and non-NaN ``float`` keys. Float infinities are
    valid and ``-0.0`` and ``0.0`` designate the same key. Keys are stored in a 2-3-4
    tree, so lookup and insertion are logarithmic in the number of entries. Values
    may be linear; use :meth:`discard_empty` after removing or iterating over all
    entries.

    With constant-time key comparison, ``len`` is ``O(1)``; lookup, insertion, and
    removal are ``O(log n)``; and consuming iteration drains the map in ``O(n)``.
    """

    # A fixed pool keeps the whole data structure statically allocated. Nodes are
    # temporarily taken out of this array for mutation and always put back before
    # another operation observes the pool.
    _nodes: array[_Node[K, V], MAX_SIZE]
    # `_free_nodes[:_free_count]` is a stack of currently unused node indices.
    _free_nodes: array[int, MAX_SIZE]
    _free_count: int
    _root: int
    _size: int
    # These transient slots bridge public operations and helpers that need to move a
    # key or value through the map without copying it. They are always `nothing` at
    # API boundaries, which `discard_empty` verifies.
    _pending: Option[tuple[K, V]]
    _query: Option[K]

    @guppy
    @no_type_check
    def __len__(self) -> int:
        """Returns the number of entries in the map in ``O(1)`` time."""
        return self._size

    @guppy
    @no_type_check
    def __iter__[K: _Ord, V, MAX_SIZE: nat](
        self: BTreeMap[K, V, MAX_SIZE] @ owned,
    ) -> BTreeMap[K, V, MAX_SIZE]:
        """Consumes the map, yielding entries in ascending key order.

        Complexity: ``O(n)`` overall.
        """
        return self

    @guppy
    @no_type_check
    def __next__[K: _Ord, V, MAX_SIZE: nat](
        self: BTreeMap[K, V, MAX_SIZE] @ owned,
    ) -> Option[tuple[tuple[K, V], BTreeMap[K, V, MAX_SIZE]]]:
        return _next_entry(self)

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
        """Returns whether the map contains ``key`` in ``O(log n)`` time."""
        _validate_key(key)
        self._query.swap(some(key)).unwrap_nothing()
        return _contains_key(self)

    @guppy
    @no_type_check
    def get[K: _Ord, V: Copy, MAX_SIZE: nat](
        self: BTreeMap[K, V, MAX_SIZE], key: K
    ) -> Option[V]:
        """Returns a copy of the value stored for ``key``, if present.

        The ``Copy`` bound is essential: the map retains its value, so a linear value
        can only be obtained by ``remove`` or consuming iteration.

        Complexity: ``O(log n)``.
        """
        _validate_key(key)
        self._query.swap(some(key)).unwrap_nothing()
        return _get(self)

    @guppy
    @no_type_check
    def insert[K: _Ord, V, MAX_SIZE: nat](
        self: BTreeMap[K, V, MAX_SIZE], key: K, value: V @ owned
    ) -> Option[V]:
        """Stores ``value`` for ``key`` and returns a displaced value, if any.

        Complexity: ``O(log n)``.
        """
        _validate_key(key)
        self._pending.swap(some((key, value))).unwrap_nothing()
        return _insert_pending(self)

    @guppy
    @no_type_check
    def remove[K: _Ord, V, MAX_SIZE: nat](
        self: BTreeMap[K, V, MAX_SIZE], key: K
    ) -> Option[V]:
        """Removes and returns the value stored for ``key``, if present.

        Complexity: ``O(log n)``.
        """
        _validate_key(key)
        location = _find(self, key)
        if location.is_nothing():
            return nothing()
        node_i, entry_i = location.unwrap()
        node = self._nodes.take(node_i)
        is_leaf = node._leaf
        self._nodes.put(node, node_i)
        if is_leaf:
            root_i = self._root
            value = _remove_leaf_descending(self, root_i, key)
            _collapse_root(self)
            return some(value)
        value = _remove_internal_entry(self, node_i, entry_i)
        _collapse_root(self)
        return some(value)


@guppy
@no_type_check
def _empty_node[K, V]() -> _Node[K, V]:
    return _Node(
        array(nothing[K]() for _ in range(3)),
        array(nothing[tuple[K, V]]() for _ in range(3)),
        array(nothing[int]() for _ in range(4)),
        0,
        True,
    )


@guppy
@no_type_check
def _validate_key[K: _Ord](key: K) -> None:
    # Comparisons are dispatched explicitly rather than using operators because the
    # private protocol is the source of these methods. This guard is shared by every
    # public key operation, preventing a non-reflexive value (notably NaN) from
    # entering the tree and making a later search path ambiguous.
    if not key.__eq__(key):
        panic("BTreeMap: key must be reflexive")


@guppy
@no_type_check
def _find[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE], key: K
) -> Option[tuple[int, int]]:
    node_i = btree_map._root
    while node_i >= 0:
        # `take` gives exclusive ownership of one node, avoiding aliases into the
        # pool while its entry/child arrays are inspected. The node is unchanged,
        # so it is immediately returned before following a child link.
        node = btree_map._nodes.take(node_i)
        entry_i = _node_entry_index(node, key)
        found = entry_i < node._size and key.__eq__(_node_key(node, entry_i))
        is_leaf = node._leaf
        next_i = -1
        if not is_leaf:
            next_i = _node_child(node, entry_i)
        btree_map._nodes.put(node, node_i)
        if found:
            return some((node_i, entry_i))
        if is_leaf:
            return nothing()
        node_i = next_i
    return nothing()


@guppy
@no_type_check
def _contains_key[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE],
) -> bool:
    key = btree_map._query.take().unwrap()
    return _find(btree_map, key).is_some()


@guppy
@no_type_check
def _get[K: _Ord, V: Copy, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE],
) -> Option[V]:
    key = btree_map._query.take().unwrap()
    location = _find(btree_map, key)
    if location.is_nothing():
        return nothing()
    node_i, entry_i = location.unwrap()
    node = btree_map._nodes.take(node_i)
    value = _node_value(node, entry_i)
    btree_map._nodes.put(node, node_i)
    return some(value)


@guppy
@no_type_check
def _remove_leaf_entry[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE], node_i: int, entry_i: int
) -> V:
    node = btree_map._nodes.take(node_i)
    _key, value = node._entries[entry_i].take().unwrap()
    node._keys[entry_i].take().unwrap()
    next_i = entry_i
    while next_i < node._size - 1:
        entry = node._entries[next_i + 1].take().unwrap()
        key = node._keys[next_i + 1].take().unwrap()
        node._entries[next_i].swap(some(entry)).unwrap_nothing()
        node._keys[next_i].swap(some(key)).unwrap_nothing()
        next_i += 1
    node._size -= 1
    is_empty_root = node_i == btree_map._root and node._size == 0
    btree_map._nodes.put(node, node_i)
    btree_map._size -= 1
    if is_empty_root:
        btree_map._root = -1
        btree_map._free_nodes[btree_map._free_count] = node_i
        btree_map._free_count += 1
    return value


@guppy
@no_type_check
def _release_node[K, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE], node_i: int
) -> None:
    """Returns an empty node slot to the static pool."""
    btree_map._free_nodes[btree_map._free_count] = node_i
    btree_map._free_count += 1


@guppy
@no_type_check
def _prepare_child[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE], parent_i: int, child_i: int
) -> int:
    """Ensures a child has at least two entries before descent."""
    parent = btree_map._nodes.take(parent_i)
    child_node_i = parent._children[child_i].unwrap()
    child = btree_map._nodes.take(child_node_i)
    child_size = child._size
    btree_map._nodes.put(child, child_node_i)
    parent_size = parent._size
    btree_map._nodes.put(parent, parent_i)
    if child_size > 1:
        return child_node_i
    if child_i > 0:
        parent = btree_map._nodes.take(parent_i)
        left_i = parent._children[child_i - 1].unwrap()
        left = btree_map._nodes.take(left_i)
        left_size = left._size
        btree_map._nodes.put(left, left_i)
        btree_map._nodes.put(parent, parent_i)
        if left_size > 1:
            _borrow_from_left(btree_map, parent_i, child_i)
            return child_node_i
    if child_i < parent_size:
        parent = btree_map._nodes.take(parent_i)
        right_i = parent._children[child_i + 1].unwrap()
        right = btree_map._nodes.take(right_i)
        right_size = right._size
        btree_map._nodes.put(right, right_i)
        btree_map._nodes.put(parent, parent_i)
        if right_size > 1:
            _borrow_from_right(btree_map, parent_i, child_i)
            return child_node_i
    if child_i > 0:
        return _merge_children(btree_map, parent_i, child_i - 1)
    return _merge_children(btree_map, parent_i, child_i)


@guppy
@no_type_check
def _remove_leaf_descending[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE], node_i: int, key: K
) -> V:
    node = btree_map._nodes.take(node_i)
    entry_i = _node_entry_index(node, key)
    is_leaf = node._leaf
    btree_map._nodes.put(node, node_i)
    if is_leaf:
        return _remove_leaf_entry(btree_map, node_i, entry_i)
    # Delete top-down: repair a one-entry child *before* descending, so deleting
    # from its subtree cannot leave it below the 2-3-4-tree minimum occupancy.
    child_i = _prepare_child(btree_map, node_i, entry_i)
    return _remove_leaf_descending(btree_map, child_i, key)


@guppy
@no_type_check
def _remove_internal_from_left[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE], parent_i: int, entry_i: int
) -> Option[V]:
    """Replaces an internal entry with its predecessor when its child can spare one."""
    parent = btree_map._nodes.take(parent_i)
    left_i = parent._children[entry_i].unwrap()
    left = btree_map._nodes.take(left_i)
    left_size = left._size
    btree_map._nodes.put(left, left_i)
    btree_map._nodes.put(parent, parent_i)
    if left_size <= 1:
        return nothing()

    predecessor_key = _rightmost_key(btree_map, left_i)
    predecessor_value = _remove_leaf_descending(btree_map, left_i, predecessor_key)
    parent = btree_map._nodes.take(parent_i)
    _old_key, old_value = parent._entries[entry_i].take().unwrap()
    parent._keys[entry_i].take().unwrap()
    parent._entries[entry_i].swap(
        some((predecessor_key, predecessor_value))
    ).unwrap_nothing()
    parent._keys[entry_i].swap(some(predecessor_key)).unwrap_nothing()
    btree_map._nodes.put(parent, parent_i)
    return some(old_value)


@guppy
@no_type_check
def _remove_internal_entry[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE], node_i: int, entry_i: int
) -> V:
    """Deletes an internal entry by borrowing, or recursively merging, its children."""
    removed = _remove_internal_from_left(btree_map, node_i, entry_i)
    if removed.is_some():
        return removed.unwrap()
    removed.unwrap_nothing()
    removed = _remove_internal_from_right(btree_map, node_i, entry_i)
    if removed.is_some():
        return removed.unwrap()
    removed.unwrap_nothing()

    parent = btree_map._nodes.take(node_i)
    left_i = parent._children[entry_i].unwrap()
    left = btree_map._nodes.take(left_i)
    left_size = left._size
    btree_map._nodes.put(left, left_i)
    btree_map._nodes.put(parent, node_i)
    merged_i = _merge_children(btree_map, node_i, entry_i)
    merged = btree_map._nodes.take(merged_i)
    is_leaf = merged._leaf
    btree_map._nodes.put(merged, merged_i)
    if is_leaf:
        return _remove_leaf_entry(btree_map, merged_i, left_size)
    return _remove_internal_entry(btree_map, merged_i, left_size)


@guppy
@no_type_check
def _rightmost_key[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE], node_i: int
) -> K:
    current_i = node_i
    while True:
        node = btree_map._nodes.take(current_i)
        size = node._size
        key = _node_key(node, size - 1)
        is_leaf = node._leaf
        next_i = -1
        if not is_leaf:
            next_i = _node_child(node, size)
        btree_map._nodes.put(node, current_i)
        if is_leaf:
            return key
        current_i = next_i


@guppy
@no_type_check
def _remove_internal_from_right[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE], parent_i: int, entry_i: int
) -> Option[V]:
    """Replaces an internal entry with its successor when its child can spare one."""
    parent = btree_map._nodes.take(parent_i)
    right_i = parent._children[entry_i + 1].unwrap()
    right = btree_map._nodes.take(right_i)
    right_size = right._size
    btree_map._nodes.put(right, right_i)
    btree_map._nodes.put(parent, parent_i)
    if right_size <= 1:
        return nothing()

    successor_key = _leftmost_key(btree_map, right_i)
    successor_value = _remove_leaf_descending(btree_map, right_i, successor_key)
    parent = btree_map._nodes.take(parent_i)
    _old_key, old_value = parent._entries[entry_i].take().unwrap()
    parent._keys[entry_i].take().unwrap()
    parent._entries[entry_i].swap(
        some((successor_key, successor_value))
    ).unwrap_nothing()
    parent._keys[entry_i].swap(some(successor_key)).unwrap_nothing()
    btree_map._nodes.put(parent, parent_i)
    return some(old_value)


@guppy
@no_type_check
def _leftmost_key[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE], node_i: int
) -> K:
    current_i = node_i
    while True:
        node = btree_map._nodes.take(current_i)
        key = _node_key(node, 0)
        is_leaf = node._leaf
        next_i = -1
        if not is_leaf:
            next_i = _node_child(node, 0)
        btree_map._nodes.put(node, current_i)
        if is_leaf:
            return key
        current_i = next_i


@guppy
@no_type_check
def _collapse_root[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE],
) -> None:
    if btree_map._root < 0:
        return
    root_i = btree_map._root
    root = btree_map._nodes.take(root_i)
    if root._size != 0 or root._leaf:
        btree_map._nodes.put(root, root_i)
        return
    # The root alone may have zero entries. Its only child becomes the new root,
    # reducing tree height and making the old root slot reusable.
    new_root_i = root._children[0].take().unwrap()
    root._leaf = True
    btree_map._nodes.put(root, root_i)
    btree_map._root = new_root_i
    _release_node(btree_map, root_i)


@guppy
@no_type_check
def _merge_children[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE], parent_i: int, entry_i: int
) -> int:
    """Merges the two minimum-sized children around a parent entry.

    Returns the index of the surviving left child. Callers must only use this when
    both children have one entry, so the merged node has exactly three entries.
    """
    parent = btree_map._nodes.take(parent_i)
    left_i = parent._children[entry_i].unwrap()
    right_i = parent._children[entry_i + 1].take().unwrap()
    left = btree_map._nodes.take(left_i)
    right = btree_map._nodes.take(right_i)
    old_left_size = left._size

    # Concatenate `left`, the separating parent entry, then `right`. Since both
    # children have one entry, the result fits exactly in a three-entry node.
    left._keys[left._size].swap(parent._keys[entry_i].take()).unwrap_nothing()
    left._entries[left._size].swap(
        some(parent._entries[entry_i].take().unwrap())
    ).unwrap_nothing()
    left._size += 1
    right_entry_i = 0
    while right_entry_i < right._size:
        left._keys[left._size].swap(right._keys[right_entry_i].take()).unwrap_nothing()
        left._entries[left._size].swap(
            some(right._entries[right_entry_i].take().unwrap())
        ).unwrap_nothing()
        left._size += 1
        right_entry_i += 1
    if not left._leaf:
        right_child_i = 0
        while right_child_i <= right._size:
            left._children[old_left_size + 1 + right_child_i].swap(
                some(right._children[right_child_i].take().unwrap())
            ).unwrap_nothing()
            right_child_i += 1

    # Removing the separator also removes the right child pointer; compact the
    # parent prefixes to preserve the node representation invariant.
    parent_entry_i = entry_i
    while parent_entry_i < parent._size - 1:
        parent._keys[parent_entry_i].swap(
            parent._keys[parent_entry_i + 1].take()
        ).unwrap_nothing()
        parent._entries[parent_entry_i].swap(
            some(parent._entries[parent_entry_i + 1].take().unwrap())
        ).unwrap_nothing()
        parent_entry_i += 1
    parent_child_i = entry_i + 1
    while parent_child_i < parent._size:
        parent._children[parent_child_i].swap(
            some(parent._children[parent_child_i + 1].take().unwrap())
        ).unwrap_nothing()
        parent_child_i += 1
    parent._size -= 1
    right._size = 0
    right._leaf = True

    btree_map._nodes.put(parent, parent_i)
    btree_map._nodes.put(left, left_i)
    btree_map._nodes.put(right, right_i)
    _release_node(btree_map, right_i)
    return left_i


@guppy
@no_type_check
def _borrow_from_left[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE], parent_i: int, child_i: int
) -> None:
    """Rotates one entry from the left sibling into ``child_i``."""
    parent = btree_map._nodes.take(parent_i)
    left_i = parent._children[child_i - 1].unwrap()
    target_i = parent._children[child_i].unwrap()
    left = btree_map._nodes.take(left_i)
    target = btree_map._nodes.take(target_i)

    # Rotate clockwise: make room at the front of the target, move the parent's
    # separator down, and promote the left sibling's largest entry to the parent.
    entry_i = target._size
    while entry_i > 0:
        target._keys[entry_i].swap(target._keys[entry_i - 1].take()).unwrap_nothing()
        target._entries[entry_i].swap(
            some(target._entries[entry_i - 1].take().unwrap())
        ).unwrap_nothing()
        entry_i -= 1
    if not target._leaf:
        child_ref_i = target._size + 1
        while child_ref_i > 0:
            target._children[child_ref_i].swap(
                some(target._children[child_ref_i - 1].take().unwrap())
            ).unwrap_nothing()
            child_ref_i -= 1
        target._children[0].swap(
            some(left._children[left._size].take().unwrap())
        ).unwrap_nothing()
    target._keys[0].swap(parent._keys[child_i - 1].take()).unwrap_nothing()
    target._entries[0].swap(
        some(parent._entries[child_i - 1].take().unwrap())
    ).unwrap_nothing()
    parent._keys[child_i - 1].swap(left._keys[left._size - 1].take()).unwrap_nothing()
    parent._entries[child_i - 1].swap(
        some(left._entries[left._size - 1].take().unwrap())
    ).unwrap_nothing()
    left._size -= 1
    target._size += 1

    btree_map._nodes.put(parent, parent_i)
    btree_map._nodes.put(left, left_i)
    btree_map._nodes.put(target, target_i)


@guppy
@no_type_check
def _borrow_from_right[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE], parent_i: int, child_i: int
) -> None:
    """Rotates one entry from the right sibling into ``child_i``."""
    parent = btree_map._nodes.take(parent_i)
    target_i = parent._children[child_i].unwrap()
    right_i = parent._children[child_i + 1].unwrap()
    target = btree_map._nodes.take(target_i)
    right = btree_map._nodes.take(right_i)

    # Mirror image of `_borrow_from_left`: append the parent's separator and
    # promote the right sibling's smallest entry after compacting that sibling.
    target._keys[target._size].swap(parent._keys[child_i].take()).unwrap_nothing()
    target._entries[target._size].swap(
        some(parent._entries[child_i].take().unwrap())
    ).unwrap_nothing()
    if not target._leaf:
        target._children[target._size + 1].swap(
            some(right._children[0].take().unwrap())
        ).unwrap_nothing()
        right_child_i = 0
        while right_child_i < right._size:
            right._children[right_child_i].swap(
                some(right._children[right_child_i + 1].take().unwrap())
            ).unwrap_nothing()
            right_child_i += 1
    parent._keys[child_i].swap(right._keys[0].take()).unwrap_nothing()
    parent._entries[child_i].swap(
        some(right._entries[0].take().unwrap())
    ).unwrap_nothing()
    right_entry_i = 0
    while right_entry_i < right._size - 1:
        right._keys[right_entry_i].swap(
            right._keys[right_entry_i + 1].take()
        ).unwrap_nothing()
        right._entries[right_entry_i].swap(
            some(right._entries[right_entry_i + 1].take().unwrap())
        ).unwrap_nothing()
        right_entry_i += 1
    right._size -= 1
    target._size += 1

    btree_map._nodes.put(parent, parent_i)
    btree_map._nodes.put(target, target_i)
    btree_map._nodes.put(right, right_i)


@guppy
@no_type_check
def _next_entry[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE] @ owned,
) -> Option[tuple[tuple[K, V], BTreeMap[K, V, MAX_SIZE]]]:
    if btree_map._size == 0:
        btree_map.discard_empty()
        return nothing()
    node_i = btree_map._root
    while True:
        node = btree_map._nodes.take(node_i)
        is_leaf = node._leaf
        if is_leaf:
            first_key = _node_key(node, 0)
            btree_map._nodes.put(node, node_i)
            break
        next_i = _node_child(node, 0)
        btree_map._nodes.put(node, node_i)
        node_i = next_i
    value = btree_map.remove(first_key).unwrap()
    return some(((first_key, value), btree_map))


@guppy
@no_type_check
def _node_entry_index[K: _Ord, V](node: _Node[K, V], key: K) -> int:
    # Lower-bound search: it returns either the matching entry or the child interval
    # that can contain the key. Equality must stop the scan, not advance past it.
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
    return node._keys[entry_i].unwrap()


@guppy
@no_type_check
def _node_value[K: _Ord, V: Copy](node: _Node[K, V], entry_i: int) -> V:
    _key, value = node._entries[entry_i].unwrap()
    return value


@guppy
@no_type_check
def _node_child[K, V](node: _Node[K, V], child_i: int) -> int:
    return node._children[child_i].unwrap()


@guppy
@no_type_check
def _insert_pending[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE],
) -> Option[V]:
    key, value = btree_map._pending.take().unwrap()
    location = _find(btree_map, key)
    if location.is_some():
        node_i, entry_i = location.unwrap()
        node = btree_map._nodes.take(node_i)
        stored_key, old_value = node._entries[entry_i].take().unwrap()
        node._entries[entry_i].swap(some((stored_key, value))).unwrap_nothing()
        btree_map._nodes.put(node, node_i)
        return some(old_value)
    if btree_map._size >= MAX_SIZE:
        panic("BTreeMap.insert: max size reached")
    if btree_map._root < 0:
        root_i = _allocate_node(btree_map)
        root = btree_map._nodes.take(root_i)
        root._keys[0].swap(some(key)).unwrap_nothing()
        root._entries[0].swap(some((key, value))).unwrap_nothing()
        root._size = 1
        btree_map._nodes.put(root, root_i)
        btree_map._root = root_i
        btree_map._size = 1
        return nothing()

    root_i = btree_map._root
    root = btree_map._nodes.take(root_i)
    root_is_full = root._size == 3
    btree_map._nodes.put(root, root_i)
    if root_is_full:
        # Split before descent. The chosen child is therefore never full when we
        # reach a leaf, guaranteeing room for the new entry without backtracking.
        new_root_i = _allocate_node(btree_map)
        new_root = btree_map._nodes.take(new_root_i)
        new_root._leaf = False
        new_root._children[0].swap(some(root_i)).unwrap_nothing()
        btree_map._nodes.put(new_root, new_root_i)
        btree_map._root = new_root_i
        _split_child(btree_map, new_root_i, 0)

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
            # A split inserts a new separator into the current node; choose the
            # appropriate half only after observing that separator.
            _split_child(btree_map, node_i, child_i)
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
        node._keys[entry_i].swap(node._keys[entry_i - 1].take()).unwrap_nothing()
        entry = node._entries[entry_i - 1].take().unwrap()
        node._entries[entry_i].swap(some(entry)).unwrap_nothing()
        entry_i -= 1
    node._keys[entry_i].swap(some(key)).unwrap_nothing()
    node._entries[entry_i].swap(some((key, value))).unwrap_nothing()
    node._size += 1
    btree_map._nodes.put(node, node_i)
    btree_map._size += 1
    return nothing()


@guppy
@no_type_check
def _allocate_node[K, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE],
) -> int:
    if btree_map._free_count <= 0:
        panic("BTreeMap: node pool exhausted")
    btree_map._free_count -= 1
    return btree_map._free_nodes[btree_map._free_count]


@guppy
@no_type_check
def _split_child[K: _Ord, V, MAX_SIZE: nat](
    btree_map: BTreeMap[K, V, MAX_SIZE], parent_i: int, child_i: int
) -> None:
    parent = btree_map._nodes.take(parent_i)
    old_child_i = parent._children[child_i].unwrap()
    child = btree_map._nodes.take(old_child_i)
    sibling_i = _allocate_node(btree_map)
    sibling = btree_map._nodes.take(sibling_i)

    sibling._leaf = child._leaf
    sibling._keys[0].swap(child._keys[2].take()).unwrap_nothing()
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
        parent._keys[parent_entry_i].swap(
            parent._keys[parent_entry_i - 1].take()
        ).unwrap_nothing()
        entry = parent._entries[parent_entry_i - 1].take().unwrap()
        parent._entries[parent_entry_i].swap(some(entry)).unwrap_nothing()
        parent_entry_i -= 1
    parent._keys[child_i].swap(child._keys[1].take()).unwrap_nothing()
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
