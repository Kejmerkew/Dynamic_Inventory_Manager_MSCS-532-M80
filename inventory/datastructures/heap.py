from __future__ import annotations
from typing import Generic, Iterable, Iterator, List, Optional, TypeVar

T = TypeVar("T")


class MinHeap(Generic[T]):
    """A binary min-heap with optional bulk heapify support."""

    __slots__ = ("_data",)

    def __init__(self, it: Optional[Iterable[T]] = None) -> None:
        self._data: List[T] = []
        if it:
            self._data = list(it)
            self._heapify()  # Bulk build in O(n) instead of repeated pushes

    # -----------------------------
    # Internal helpers
    # -----------------------------
    def _sift_up(self, idx: int) -> None:
        data = self._data
        while idx > 0:
            parent = (idx - 1) // 2
            if data[parent] <= data[idx]:
                break
            data[parent], data[idx] = data[idx], data[parent]
            idx = parent

    def _sift_down(self, idx: int) -> None:
        data = self._data
        n = len(data)
        while True:
            left = 2 * idx + 1
            right = 2 * idx + 2
            smallest = idx
            if left < n and data[left] < data[smallest]:
                smallest = left
            if right < n and data[right] < data[smallest]:
                smallest = right
            if smallest == idx:
                break
            data[idx], data[smallest] = data[smallest], data[idx]
            idx = smallest

    def _heapify(self) -> None:
        """Transform the current list into a heap in-place in O(n) time."""
        n = len(self._data)
        for i in reversed(range(n // 2)):
            self._sift_down(i)

    # -----------------------------
    # Public API
    # -----------------------------
    def push(self, item: T) -> None:
        """Push item onto the heap (O(log n))."""
        self._data.append(item)
        self._sift_up(len(self._data) - 1)

    def pop(self) -> T:
        """Pop and return the smallest item (O(log n))."""
        if not self._data:
            raise IndexError("pop from empty heap")
        data = self._data
        top = data[0]
        last = data.pop()
        if data:
            data[0] = last
            self._sift_down(0)
        return top

    def peek(self) -> Optional[T]:
        """Return the smallest item without removing it (O(1))."""
        return self._data[0] if self._data else None

    def replace(self, item: T) -> T:
        """Pop and return the smallest item, then push a new item (O(log n))."""
        if not self._data:
            raise IndexError("replace on empty heap")
        top = self._data[0]
        self._data[0] = item
        self._sift_down(0)
        return top

    def pushpop(self, item: T) -> T:
        """Push item then pop smallest in a single O(log n) operation."""
        if self._data and self._data[0] < item:
            item, self._data[0] = self._data[0], item
            self._sift_down(0)
        return item

    def __len__(self) -> int:
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