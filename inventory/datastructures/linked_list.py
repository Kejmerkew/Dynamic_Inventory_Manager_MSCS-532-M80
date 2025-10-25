from __future__ import annotations
from typing import Generic, Iterator, Optional, Tuple, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class _LLNode(Generic[K, V]):
    """A lightweight node for a singly-linked list (used by HashMap buckets)."""

    __slots__ = ("key", "value", "next")

    def __init__(self, key: Optional[K] = None, value: Optional[V] = None, next: Optional["_LLNode[K, V]"] = None) -> None:
        self.key = key
        self.value = value
        self.next = next


class LinkedList(Generic[K, V]):
    """Simple singly-linked list specialized for (key, value) pairs.

    Supports insertion-or-replacement, search by key, deletion by key,
    and iteration over (key, value) pairs.
    """

    __slots__ = ("head",)

    def __init__(self) -> None:
        self.head: Optional[_LLNode[K, V]] = None

    def insert_or_replace(self, key: K, value: V) -> bool:
        """Insert new (key, value) at head if key not present; otherwise replace.

        Returns True if a new node was inserted; False if an existing node was
        found and its value replaced.
        """
        n = self.head
        while n:
            if n.key == key:
                n.value = value
                return False  # replaced
            n = n.next
        self.head = _LLNode(key, value, self.head)
        return True  # inserted new

    def find(self, key: K) -> Optional[V]:
        """Return the value for *key*, or None if not present."""
        n = self.head
        while n:
            if n.key == key:
                return n.value  # type: ignore[return-value]
            n = n.next
        return None

    def delete(self, key: K) -> bool:
        """Delete node with *key* if present; return True if deleted, else False."""
        prev: Optional[_LLNode[K, V]] = None
        cur = self.head
        while cur:
            if cur.key == key:
                if prev:
                    prev.next = cur.next
                else:
                    self.head = cur.next
                return True
            prev, cur = cur, cur.next
        return False

    def items(self) -> Iterator[Tuple[K, V]]:
        """Yield (key, value) pairs in list order."""
        n = self.head
        while n:
            yield (n.key, n.value)  # type: ignore[misc]
            n = n.next