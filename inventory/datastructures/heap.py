from __future__ import annotations
from typing import Generic, Iterable, Iterator, List, Optional, TypeVar

T = TypeVar("T")


class MinHeap(Generic[T]):
    """A binary min-heap.

    Assumes that stored elements are mutually comparable (support ``<`` and ``<=``).
    """

    __slots__ = ("_data",)

    def __init__(self, it: Optional[Iterable[T]] = None) -> None:
        self._data: List[T] = []
        if it:
            for x in it:
                self.push(x)

    def _sift_up(self, idx: int) -> None:
        while idx > 0:
            parent = (idx - 1) // 2
            if self._data[parent] <= self._data[idx]:
                break
            self._data[parent], self._data[idx] = self._data[idx], self._data[parent]
            idx = parent

    def _sift_down(self, idx: int) -> None:
        n = len(self._data)
        while True:
            left = 2 * idx + 1
            right = 2 * idx + 2
            smallest = idx
            if left < n and self._data[left] < self._data[smallest]:
                smallest = left
            if right < n and self._data[right] < self._data[smallest]:
                smallest = right
            if smallest == idx:
                break
            self._data[idx], self._data[smallest] = self._data[smallest], self._data[idx]
            idx = smallest

    def push(self, item: T) -> None:
        """Push *item* onto the heap."""
        self._data.append(item)
        self._sift_up(len(self._data) - 1)

    def pop(self) -> T:
        """Pop and return the smallest item.

        Raises:
            IndexError: if the heap is empty.
        """
        if not self._data:
            raise IndexError("pop from empty heap")
        top = self._data[0]
        last = self._data.pop()
        if self._data:
            self._data[0] = last
            self._sift_down(0)
        return top

    def peek(self) -> Optional[T]:
        """Return the smallest item without removing it, or None if empty."""
        return self._data[0] if self._data else None

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._data)

    def __bool__(self) -> bool:  # pragma: no cover - trivial
        return bool(self._data)

    def to_list(self) -> List[T]:  # pragma: no cover - trivial
        return list(self._data)

    def __iter__(self) -> Iterator[T]:  # pragma: no cover - simple
        # Iterate over the internal array (heap order, not sorted order)
        return iter(self._data)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"MinHeap({self._data!r})"