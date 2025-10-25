from __future__ import annotations
import ctypes
from typing import Generic, Iterable, Iterator, Optional, TypeVar, overload

T = TypeVar("T")
U = TypeVar("U")


class CustomList(Generic[T]):
    """A thin, typed list-like container implemented via a dynamic array.

    Implementation notes
    --------------------
    • Storage is a ctypes array of `py_object` (not Python's built-in list).
    • Capacity grows geometrically (x2) when full; optionally shrinks on pops.
    • Negative indices are normalized (like built-in list semantics).
    • Slicing returns another CustomList[T].
    • `.get()` is a safe accessor that never raises IndexError.
    """

    __slots__ = ("_buf", "_size", "_capacity")

    # Initial allocated capacity for the dynamic array.
    _INITIAL_CAPACITY = 4

    def __init__(self, it: Optional[Iterable[T]] = None) -> None:
        # Allocate an initial buffer and start empty.
        self._capacity = self._INITIAL_CAPACITY
        self._buf = self._make_array(self._capacity)
        self._size = 0

        # If an iterable is provided, append its items one-by-one
        # (reuses our own append to benefit from growth policy).
        if it is not None:
            for v in it:
                self.append(v)

    # ------------------------------- internals -------------------------------

    @staticmethod
    def _make_array(capacity: int):
        """Allocate a raw ctypes array of length `capacity` to hold py_object."""
        if capacity <= 0:
            capacity = 1  # never allow a zero-length buffer
        return (capacity * ctypes.py_object)()

    def _resize(self, new_capacity: int) -> None:
        """Resize internal buffer to `new_capacity` (must be ≥ current size).

        Copies existing elements into a new buffer and updates capacity.
        """
        if new_capacity < self._size:
            raise ValueError("new capacity must be >= size")

        new_buf = self._make_array(new_capacity)

        # Copy live items into the new buffer.
        for i in range(self._size):
            new_buf[i] = self._buf[i]

        # (Optional) Help GC by clearing old references beyond _size.
        # Not strictly required, but keeps memory graphs tidy.
        for i in range(self._size, self._capacity):
            try:
                self._buf[i] = None  # type: ignore[assignment]
            except Exception:
                break

        self._buf = new_buf
        self._capacity = new_capacity

    def _grow_if_full(self) -> None:
        """Double capacity when the buffer is full (amortized O(1) append)."""
        if self._size >= self._capacity:
            self._resize(self._capacity * 2 if self._capacity > 0 else self._INITIAL_CAPACITY)

    @staticmethod
    def _normalize_index(idx: int, size: int) -> int:
        """Map negative indices and validate bounds.

        Returns the non-negative index in [0, size).
        Raises IndexError if out of range.
        """
        if idx < 0:
            idx += size
        if idx < 0 or idx >= size:
            raise IndexError("list index out of range")
        return idx

    # --------------------------------- API -----------------------------------

    def append(self, value: T) -> None:
        """Append `value` to the end. Amortized O(1)."""
        self._grow_if_full()
        self._buf[self._size] = value
        self._size += 1

    def extend(self, it: Iterable[T]) -> None:
        """Append all elements from `it` in order. O(n) in number of items."""
        for v in it:
            self.append(v)

    def pop(self, idx: int = -1) -> T:
        """Remove and return the item at `idx` (default: last).

        Complexity: O(n - idx) due to left-shift of trailing elements.

        Raises:
            IndexError: if the list is empty or idx is out of range.
        """
        if self._size == 0:
            raise IndexError("pop from empty list")

        i = self._normalize_index(idx, self._size)
        val = self._buf[i]  # type: ignore[assignment]

        # Shift elements left to fill the gap.
        for j in range(i, self._size - 1):
            self._buf[j] = self._buf[j + 1]

        # Clear the now-unused last slot and shrink size.
        self._buf[self._size - 1] = None
        self._size -= 1

        # (Optional) Shrink capacity when quarter-full to save memory.
        if self._capacity > self._INITIAL_CAPACITY and self._size <= self._capacity // 4:
            self._resize(max(self._INITIAL_CAPACITY, self._capacity // 2))

        return val  # type: ignore[return-value]

    def remove(self, value: T) -> None:
        """Remove first occurrence of `value`. O(n).

        Raises:
            ValueError: if `value` is not present.
        """
        for i in range(self._size):
            if self._buf[i] == value:
                self.pop(i)
                return
        raise ValueError(f"{value!r} not in CustomList")
    
    def remove_optimized(self, value: T) -> None:
        """Remove first occurrence of `value` without preserving order. O(1) amortized."""
        for i in range(self._size):
            if self._buf[i] == value:
                self._buf[i] = self._buf[self._size - 1]  # Swap with last element
                self._buf[self._size - 1] = None
                self._size -= 1
                # Optional shrink
                if self._capacity > self._INITIAL_CAPACITY and self._size <= self._capacity // 4:
                    self._resize(max(self._INITIAL_CAPACITY, self._capacity // 2))
                return
        raise ValueError(f"{value!r} not in CustomList")


    def clear(self) -> None:
        """Remove all items. Keeps capacity to avoid churn on re-use."""
        for i in range(self._size):
            self._buf[i] = None
        self._size = 0
        # If you prefer to free memory more aggressively, you can:
        # self._resize(self._INITIAL_CAPACITY)

    def __len__(self) -> int:
        """Number of stored elements. O(1)."""
        return self._size

    def __iter__(self) -> Iterator[T]:
        """Yield items from left to right."""
        for i in range(self._size):
            yield self._buf[i]  # type: ignore[misc]

    def __getitem__(self, idx: int | slice) -> T | "CustomList[T]":
        """Get an item or a slice.

        • `lst[i]` returns the element at i (supports negative indices).
        • `lst[a:b:c]` returns a new CustomList with the slice.
        """
        if isinstance(idx, slice):
            # Convert slice into concrete start/stop/step relative to current size.
            # Note: slice.indices will raise ValueError if step == 0, matching list semantics.
            start, stop, step = idx.indices(self._size)
            out: CustomList[T] = CustomList()
            for i in range(start, stop, step):
                out.append(self._buf[i])  # type: ignore[misc]
            return out

        i = self._normalize_index(idx, self._size)
        return self._buf[i]  # type: ignore[return-value]

    def __setitem__(self, idx: int, value: T) -> None:
        """Set the element at `idx` to `value` (supports negative indices)."""
        i = self._normalize_index(idx, self._size)
        self._buf[i] = value

    def __contains__(self, value: T) -> bool:
        """Return True if `value` is present (linear scan)."""
        for i in range(self._size):
            if self._buf[i] == value:
                return True
        return False

    def index(self, value: T) -> int:
        """Return first index of `value`. O(n).

        Raises:
            ValueError: if the value is not present.
        """
        for i in range(self._size):
            if self._buf[i] == value:
                return i
        raise ValueError(f"{value!r} is not in CustomList")

    @overload
    def get(self, idx: int) -> Optional[T]: ...
    @overload
    def get(self, idx: int, default: U) -> T | U: ...

    def get(self, idx: int, default: U | None = None) -> T | U | None:
        """Safe accessor: return item at `idx` or `default` if out of range.

        • Never raises IndexError.
        • Supports negative indices.
        """
        try:
            i = self._normalize_index(idx, self._size)
            return self._buf[i]  # type: ignore[return-value]
        except IndexError:
            return default

    def to_py(self) -> CustomList[object]:
        """Convert to a plain Python `list`.

        If an element implements `to_py()`, that method is used to convert it,
        enabling recursive conversion of custom objects.
        """
        out: CustomList[object] = []
        for i in range(self._size):
            v = self._buf[i]
            if hasattr(v, "to_py") and callable(getattr(v, "to_py")):
                out.append(v.to_py())  # type: ignore[call-arg]
            else:
                out.append(v)
        return out

    def __bool__(self) -> bool:  # pragma: no cover - trivial
        """Truthiness: non-empty containers are True."""
        return self._size != 0

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """Debug representation showing Python-list form of the contents."""
        return f"CustomList({self.to_py()!r})"
    

