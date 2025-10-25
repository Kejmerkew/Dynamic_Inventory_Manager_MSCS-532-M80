from __future__ import annotations
from typing import Generic, Iterable, Iterator, Optional, Tuple, TypeVar

from .hash_map import HashMap

K = TypeVar("K")
V = TypeVar("V")

class Dictionary(Generic[K, V]):
    """A mapping-like wrapper around HashMap with optimized performance and memory usage."""

    __slots__ = ("_map",)

    def __init__(self, it: Optional[Iterable[Tuple[K, V]]] = None, **kwargs: V) -> None:
        self._map: HashMap[K, V] = HashMap()
        # Bulk insert if iterable provided
        if it is not None:
            if hasattr(it, "items"):  # dict-like
                self._map.bulk_set(it.items())  # assume HashMap.bulk_set exists
            else:
                self._map.bulk_set(it)
        if kwargs:
            self._map.bulk_set(kwargs.items())

    # ---------------------------
    # Item access
    # ---------------------------
    def __setitem__(self, key: K, value: V) -> None:
        self._map.set(key, value)

    def __getitem__(self, key: K) -> V:
        sentinel = object()
        val = self._map.get(key, sentinel)
        if val is sentinel:
            raise KeyError(key)
        return val

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        return self._map.get(key, default)

    def __contains__(self, key: K) -> bool:
        return self._map.contains(key)

    def __len__(self) -> int:
        return len(self._map)

    def __iter__(self) -> Iterator[K]:
        return self._map.keys()

    # ---------------------------
    # Iterators (lazy)
    # ---------------------------
    def keys(self) -> Iterator[K]:
        """Return an iterator over keys (lazy, no full copy)."""
        return self._map.keys()

    def values(self) -> Iterator[V]:
        """Return an iterator over values (lazy, no full copy)."""
        return self._map.values()

    def items(self) -> Iterator[Tuple[K, V]]:
        """Return an iterator over key-value pairs (lazy, no full copy)."""
        return self._map.items()

    # ---------------------------
    # Conversion
    # ---------------------------
    def to_py(self, recursive: bool = True) -> dict[K, V]:
        """Convert to a native dict. Optionally convert values recursively."""
        d: dict[K, V] = {}
        for k, v in self._map.items():
            if recursive and hasattr(v, "to_py") and callable(getattr(v, "to_py")):
                d[k] = v.to_py()  # type: ignore[assignment]
            else:
                d[k] = v
        return d

    def __repr__(self) -> str:
        return f"Dictionary({self.to_py()!r})"
