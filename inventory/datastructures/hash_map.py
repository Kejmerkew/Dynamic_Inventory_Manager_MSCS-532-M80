from __future__ import annotations
from typing import Generic, Iterator, Optional, Tuple, TypeVar, Iterable

from .linked_list import LinkedList

K = TypeVar("K")
V = TypeVar("V")


class HashMap(Generic[K, V]):
    """A high-performance separate-chaining hash table.

    Optimizations:
    - Resize inserts directly into new buckets to avoid repeated _resize checks.
    - Bulk insertion precomputes final capacity and inserts efficiently.
    - Lazy bucket creation to reduce memory for sparse tables.
    - Supports fast iteration over keys, values, and items.
    """

    __slots__ = ("_cap", "_load", "_buckets", "_size")

    def __init__(self, capacity: int = 16, load_factor: float = 0.75) -> None:
        if capacity < 4:
            capacity = 4
        if not (0.1 <= load_factor < 1.0):
            raise ValueError("load_factor must be in [0.1, 1.0)")
        self._cap: int = capacity
        self._load: float = load_factor
        # Lazy bucket creation: only create LinkedList when needed
        self._buckets: list[Optional[LinkedList[K, V]]] = [None] * self._cap
        self._size: int = 0

    # -----------------------------
    # Internal helpers
    # -----------------------------
    def _bucket_index(self, key: K) -> int:
        """Compute bucket index for a key (power-of-two optimization)."""
        h = hash(key)
        return h & (self._cap - 1) if (self._cap & (self._cap - 1)) == 0 else h % self._cap

    def _resize(self) -> None:
        """Double the capacity and rehash all entries directly."""
        old_buckets = self._buckets
        self._cap *= 2
        self._buckets = [None] * self._cap
        self._size = 0

        for bucket in old_buckets:
            if bucket is None:
                continue
            for k, v in bucket.items():
                idx = self._bucket_index(k)
                if self._buckets[idx] is None:
                    self._buckets[idx] = LinkedList()
                self._buckets[idx].insert_or_replace(k, v)
                self._size += 1

    # -----------------------------
    # Core operations
    # -----------------------------
    def set(self, key: K, value: V) -> None:
        """Insert or update key-value pair."""
        idx = self._bucket_index(key)
        if self._buckets[idx] is None:
            self._buckets[idx] = LinkedList()
        inserted = self._buckets[idx].insert_or_replace(key, value)
        if inserted:
            self._size += 1
            if self._size / self._cap > self._load:
                self._resize()

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        """Retrieve value for key or return default."""
        idx = self._bucket_index(key)
        bucket = self._buckets[idx]
        if bucket is None:
            return default
        v = bucket.find(key)
        return default if v is None else v

    def contains(self, key: K) -> bool:
        """Check if key exists in the map."""
        idx = self._bucket_index(key)
        bucket = self._buckets[idx]
        return bucket.find(key) is not None if bucket else False

    def delete(self, key: K) -> bool:
        """Remove key if present."""
        idx = self._bucket_index(key)
        bucket = self._buckets[idx]
        if bucket and bucket.delete(key):
            self._size -= 1
            return True
        return False

    # -----------------------------
    # Bulk insertion
    # -----------------------------
    def bulk_set(self, items: Iterable[Tuple[K, V]]) -> None:
        """Insert multiple key-value pairs efficiently."""
        if not isinstance(items, (list, tuple)):
            items = list(items)
        needed_capacity = int(len(items) / self._load) + 1
        if needed_capacity > self._cap:
            while self._cap < needed_capacity:
                self._cap *= 2
            self._buckets = [None] * self._cap
            self._size = 0

        for k, v in items:
            self.set(k, v)

    # -----------------------------
    # Iteration helpers
    # -----------------------------
    def items(self) -> Iterator[Tuple[K, V]]:
        for bucket in self._buckets:
            if bucket:
                yield from bucket.items()

    def keys(self) -> Iterator[K]:
        for k, _ in self.items():
            yield k

    def values(self) -> Iterator[V]:
        for _, v in self.items():
            yield v

    # -----------------------------
    # Standard magic methods
    # -----------------------------
    def __len__(self) -> int:  # pragma: no cover - trivial
        return self._size

    def __iter__(self) -> Iterator[K]:  # pragma: no cover - simple
        return self.keys()

    def __repr__(self) -> str:  # pragma: no cover - trivial
        pairs = ", ".join(f"{k!r}: {v!r}" for k, v in self.items())
        return f"HashMap({{{pairs}}})"