from __future__ import annotations
from typing import Generic, Iterator, Optional, Tuple, TypeVar

from .linked_list import LinkedList

K = TypeVar("K")
V = TypeVar("V")


class HashMap(Generic[K, V]):
    """A separate-chaining hash table.

    *This maintains the spirit of your original implementation with improvements:*
    - Input validation for capacity/load factor
    - Clear docs and type hints
    - Iteration helpers for keys/values/items
    - Resize on threshold and power-of-two optimization when possible
    """

    __slots__ = ("_cap", "_load", "_buckets", "_size")

    def __init__(self, capacity: int = 16, load_factor: float = 0.75) -> None:
        if capacity < 4:
            capacity = 4
        if not (0.1 <= load_factor < 1.0):
            raise ValueError("load_factor must be in [0.1, 1.0)")
        self._cap: int = capacity
        self._load: float = load_factor
        self._buckets: list[LinkedList[K, V]] = [LinkedList() for _ in range(self._cap)]
        self._size: int = 0

    def _bucket_index(self, key: K) -> int:
        # Power-of-two fast path if capacity is a power of two; otherwise fallback to modulo
        h = hash(key)
        return h & (self._cap - 1) if (self._cap & (self._cap - 1)) == 0 else h % self._cap

    def _resize(self) -> None:
        # Double capacity and rehash all existing entries
        old_buckets = self._buckets
        self._cap *= 2
        self._buckets = [LinkedList() for _ in range(self._cap)]
        self._size = 0
        for ll in old_buckets:
            for k, v in ll.items():
                self.set(k, v)

    def set(self, key: K, value: V) -> None:
        """Insert or update *key* with *value*. Resizes when load factor exceeded."""
        idx = self._bucket_index(key)
        inserted = self._buckets[idx].insert_or_replace(key, value)
        if inserted:
            self._size += 1
            if self._size / self._cap > self._load:
                self._resize()

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        """Return value for *key* if present; otherwise *default*."""
        idx = self._bucket_index(key)
        v = self._buckets[idx].find(key)
        return default if v is None else v

    def contains(self, key: K) -> bool:
        """True if *key* is present in the map."""
        idx = self._bucket_index(key)
        return self._buckets[idx].find(key) is not None

    def delete(self, key: K) -> bool:
        """Remove *key* if present. Returns True on success, False otherwise."""
        idx = self._bucket_index(key)
        if self._buckets[idx].delete(key):
            self._size -= 1
            return True
        return False

    def items(self) -> Iterator[Tuple[K, V]]:
        for ll in self._buckets:
            yield from ll.items()

    def keys(self) -> Iterator[K]:
        for k, _ in self.items():
            yield k

    def values(self) -> Iterator[V]:
        for _, v in self.items():
            yield v

    def __len__(self) -> int:  # pragma: no cover - trivial
        return self._size

    def __iter__(self) -> Iterator[K]:  # pragma: no cover - simple
        return self.keys()

    def __repr__(self) -> str:  # pragma: no cover - trivial
        pairs = ", ".join(f"{k!r}: {v!r}" for k, v in self.items())
        return f"HashMap({{{pairs}}})"