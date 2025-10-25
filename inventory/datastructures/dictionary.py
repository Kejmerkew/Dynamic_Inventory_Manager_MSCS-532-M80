from __future__ import annotations
from typing import Generic, Iterable, Iterator, Optional, Tuple, TypeVar

from .custom_list import CustomList
from .hash_map import HashMap

K = TypeVar("K")
V = TypeVar("V")


class Dictionary(Generic[K, V]):
    """A minimal mapping-like wrapper around :class:`HashMap`.

    Keeps your original API and behavior while adding typing and docs.
    """

    __slots__ = ("_map",)

    def __init__(self, it: Optional[Iterable[Tuple[K, V]]] = None, **kwargs: V) -> None:
        self._map: HashMap[K, V] = HashMap()
        if it is not None:
            # Accept dict-like or iterable of pairs
            if hasattr(it, "items"):
                for k, v in it.items():  # type: ignore[attr-defined]
                    self[k] = v
            else:
                for k, v in it:
                    self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def __setitem__(self, key: K, value: V) -> None:
        self._map.set(key, value)

    def __getitem__(self, key: K) -> V:
        val = self._map.get(key, None)
        if val is None and not self._map.contains(key):
            raise KeyError(key)
        return val  # type: ignore[return-value]

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        return self._map.get(key, default)

    def __contains__(self, key: K) -> bool:  # pragma: no cover - trivial
        return self._map.contains(key)

    def keys(self) -> CustomList[K]:
        # Materialize into a CustomList for stability
        return CustomList(self._map.keys())

    def values(self) -> CustomList[V]:
        return CustomList(self._map.values())

    def items(self) -> CustomList[Tuple[K, V]]:
        return CustomList(self._map.items())

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._map)

    def to_py(self) -> dict[K, V]:
        """Convert to a native *dict*; recursively uses ``to_py`` when present."""
        d: dict[K, V] = {}
        for k, v in self._map.items():
            if hasattr(v, "to_py") and callable(getattr(v, "to_py")):
                d[k] = v.to_py()  # type: ignore[assignment]
            else:
                d[k] = v
        return d

    def __iter__(self) -> Iterator[K]:  # pragma: no cover - simple
        # Iterate over keys to match dict-like iteration
        return iter(self._map.keys())

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"Dictionary({self.to_py()!r})"