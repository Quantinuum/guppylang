"""Guppy standard library collections."""

from guppylang.std.collections.btree_map import BTreeMap, empty_btree_map
from guppylang.std.collections.priority_queue import PriorityQueue, empty_priority_queue
from guppylang.std.collections.queue import Queue, empty_queue
from guppylang.std.collections.stack import Stack, empty_stack

__all__ = [
    "BTreeMap",
    "PriorityQueue",
    "Queue",
    "Stack",
    "empty_btree_map",
    "empty_priority_queue",
    "empty_queue",
    "empty_stack",
]
