import os
import sys
import csv
import random
import time
import statistics
import sys as py_sys  # to differentiate from the path sys

# Ensure we can import from the project
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from inventory.datastructures.custom_list import CustomList

# ----------------------------
# Helper Functions
# ----------------------------

def generate_random_list(size: int):
    """Generate a list of random integers of given size."""
    return [random.randint(0, 1000000) for _ in range(size)]

def measure_operation_time(operation, input_size: int, iterations: int = 5):
    """Run the operation multiple times and return average + std deviation (ms)."""
    times = []
    space_used = []
    for _ in range(iterations):
        data = generate_random_list(input_size)
        start = time.perf_counter()
        c = operation(data)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # convert to milliseconds
        space_used.append(measure_true_space(c))

    avg_time = statistics.mean(times)
    std_time = statistics.stdev(times) if len(times) > 1 else 0.0
    avg_space = statistics.mean(space_used)
    std_space = statistics.stdev(space_used) if len(space_used) > 1 else 0.0
    return avg_time, std_time, avg_space, std_space

def measure_true_space(c: CustomList):
    """Estimate total memory usage of CustomList including its buffer."""
    total = py_sys.getsizeof(c)  # CustomList object itself
    if hasattr(c, "_buf"):
        total += py_sys.getsizeof(c._buf)  # ctypes array
        for i in range(len(c)):
            total += py_sys.getsizeof(c._buf[i])
    return total

# ----------------------------
# Operations to Benchmark
# ----------------------------

def test_append(data):
    c = CustomList()
    for item in data:
        c.append(item)
    return c

def test_pop(data):
    c = CustomList()
    for item in data:
        c.append(item)
    while len(c) > 0:
        c.pop()
    return c

def test_remove(data):
    c = CustomList()
    for item in data:
        c.append(item)
    n = len(data)
    for item in range(n, n - 3, -1):
        try:
            c.remove(item)
        except ValueError:
            pass
    return c

def test_get(data):
    c = CustomList()
    for item in data:
        c.append(item)
    n = len(data)
    for item in range(n, n-3, -1):
        _ = c.get(item)
    return c

def test_remove_optimized(data):
    c = CustomList()
    for item in data:
        c.append(item)
    n = len(data)
    for item in range(n, n-3, -1):
        try:
            c.remove_optimized(item)
        except ValueError:
            pass
    return c

# ----------------------------
# Benchmark Runner
# ----------------------------

def run_benchmarks(output_file: str, base_input: int = 1000):
    """Run exponential performance tests for CustomList operations."""
    operations = {
        "append": test_append,
        "pop": test_pop,
        "get": test_get,
        "remove": test_remove,
        "remove_optimized": test_remove_optimized,
    }

    input_sizes = [base_input * (2 ** i) for i in range(12)]

    with open(output_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "Input Size",
            "Operation",
            "Average Time (ms)",
            "Std Dev Time (ms)",
            "Average Space (bytes)",
            "Std Dev Space (bytes)"
        ])

        for op_name, op_func in operations.items():
            for size in input_sizes:
                avg_time, std_time, avg_space, std_space = measure_operation_time(op_func, size)
                writer.writerow([
                    size,
                    op_name,
                    f"{avg_time:.3f}",
                    f"{std_time:.3f}",
                    f"{avg_space:.0f}",
                    f"{std_space:.0f}"
                ])
                print(f"{op_name:<18} | Size: {size:<8} | Avg Time: {avg_time:.3f} ms | Std Time: {std_time:.3f} ms | Avg Space: {avg_space:.0f} B | Std Space: {std_space:.0f} B")

    print(f"\nBenchmark completed. Results saved to {output_file}")

# ----------------------------
# Main Entry Point
# ----------------------------

if __name__ == "__main__":
    OUTPUT_CSV = "custom_list_performance_optimized_with_space.csv"
    run_benchmarks(OUTPUT_CSV, base_input=100)
