import os
import sys

# Add the parent directory (project root) to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import random
import statistics
import argparse

from inventory.datastructures.custom_list import CustomList
from inventory.datastructures.dictionary import Dictionary
from inventory.datastructures.hash_map import HashMap
from inventory.datastructures.heap import MinHeap


def generate_random_input(size: int):
    """Generate a list of random integers of the given size."""
    return [random.randint(0, 10_000) for _ in range(size)]


def benchmark_append(size: int):
    times = []
    for _ in range(5):  # Run 5 trials
        data = generate_random_input(size)
        custom_list = CustomList()
        start = time.perf_counter()
        for item in data:
            custom_list.append(item)
        end = time.perf_counter()
        times.append(end - start)
    return statistics.mean(times), statistics.stdev(times)


def benchmark_pop(size: int):
    times = []
    for _ in range(5):
        data = generate_random_input(size)
        custom_list = CustomList()
        for item in data:
            custom_list.append(item)
        start = time.perf_counter()
        for _ in range(size):
            custom_list.pop()
        end = time.perf_counter()
        times.append(end - start)
    return statistics.mean(times), statistics.stdev(times)


def benchmark_remove(size: int):
    times = []
    for _ in range(5):
        data = generate_random_input(size)
        custom_list = CustomList()
        for item in data:
            custom_list.append(item)
        start = time.perf_counter()
        for item in data:
            custom_list.remove(item)
        end = time.perf_counter()
        times.append(end - start)
    return statistics.mean(times), statistics.stdev(times)


def benchmark_get(size: int):
    times = []
    for _ in range(5):
        data = generate_random_input(size)
        custom_list = CustomList()
        for item in data:
            custom_list.append(item)
        indices = [random.randint(0, size - 1) for _ in range(size)]
        start = time.perf_counter()
        for idx in indices:
            _ = custom_list.get(idx)
        end = time.perf_counter()
        times.append(end - start)
    return statistics.mean(times), statistics.stdev(times)


def main():
    parser = argparse.ArgumentParser(description="Benchmark operations on CustomList.")
    parser.add_argument("operation", choices=["append", "pop", "remove", "get"], help="Operation to benchmark")
    parser.add_argument("size", type=int, help="Size of input data")
    args = parser.parse_args()

    op = args.operation
    size = args.size

    if op == "append":
        mean, std = benchmark_append(size)
    elif op == "pop":
        mean, std = benchmark_pop(size)
    elif op == "remove":
        mean, std = benchmark_remove(size)
    elif op == "get":
        mean, std = benchmark_get(size)

    print(f"\n=== Benchmark Results for CustomList.{op}() ===")
    print(f"Input size: {size}")
    print(f"Average time (5 runs): {mean:.6f}s")
    print(f"Standard deviation:   {std:.6f}s")
    print("=============================================\n")


if __name__ == "__main__":
    main()
