import os
import sys
import csv
import random
import time
import statistics

# Ensure we can import from the project
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from inventory.datastructures.hash_map import HashMap

# ----------------------------
# Helper Functions
# ----------------------------

def generate_random_pairs(size: int):
    """Generate a list of random key-value pairs."""
    return [(random.randint(0, size * 10), random.randint(0, 1000000)) for _ in range(size)]

def measure_operation_time(operation, input_size: int, iterations: int = 5):
    """Run the operation multiple times and return average + std deviation (ms)."""
    times = []
    for _ in range(iterations):
        data = generate_random_pairs(input_size)
        start = time.perf_counter()
        operation(data)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # convert to milliseconds

    avg_time = statistics.mean(times)
    std_dev = statistics.stdev(times) if len(times) > 1 else 0.0
    return avg_time, std_dev

def measure_space_efficiency(operation, input_size: int, iterations: int = 3):
    """Return average memory used by the HashMap (bytes)."""
    import sys
    sizes = []
    for _ in range(iterations):
        data = generate_random_pairs(input_size)
        hm = operation(data)
        total_size = sys.getsizeof(hm)  # size of HashMap object itself

        # Add sizes of keys and values in all buckets
        for k, v in hm.items():
            total_size += sys.getsizeof(k)
            total_size += sys.getsizeof(v)
        sizes.append(total_size)
    avg_size = statistics.mean(sizes)
    return avg_size

# ----------------------------
# Operations to Benchmark
# ----------------------------

def test_set(data):
    hm = HashMap()
    for k, v in data:
        hm.set(k, v)
    return hm

def test_get(data):
    hm = HashMap()
    for k, v in data:
        hm.set(k, v)
    for k, _ in data[:3]:
        _ = hm.get(k)
    return hm

def test_contains(data):
    hm = HashMap()
    for k, v in data:
        hm.set(k, v)
    for k, _ in data[:3]:
        _ = hm.contains(k)
    return hm

def test_delete(data):
    hm = HashMap()
    for k, v in data:
        hm.set(k, v)
    for k, _ in data[:3]:
        hm.delete(k)
    return hm

def test_keys(data):
    hm = HashMap()
    for k, v in data:
        hm.set(k, v)
    _ = list(hm.keys())
    return hm

def test_values(data):
    hm = HashMap()
    for k, v in data:
        hm.set(k, v)
    _ = list(hm.values())
    return hm

def test_items(data):
    hm = HashMap()
    for k, v in data:
        hm.set(k, v)
    _ = list(hm.items())
    return hm

# ----------------------------
# Benchmark Runner
# ----------------------------

def run_benchmarks(output_file: str, base_input: int = 100):
    """Run exponential performance tests for HashMap operations."""
    operations = {
        "set": test_set,
        "get": test_get,
        "contains": test_contains,
        "delete": test_delete,
        "keys": test_keys,
        "values": test_values,
        "items": test_items
    }

    input_sizes = [base_input * (2 ** i) for i in range(12)]

    with open(output_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "Input Size",
            "Operation",
            "Average Time (ms)",
            "Standard Deviation (ms)",
            "Average Space (bytes)"
        ])

        for op_name, op_func in operations.items():
            for size in input_sizes:
                avg_time, std_time = measure_operation_time(op_func, size)
                avg_space = measure_space_efficiency(op_func, size)
                writer.writerow([size, op_name, f"{avg_time:.3f}", f"{std_time:.3f}", f"{avg_space:.0f}"])
                print(f"{op_name:<10} | Size: {size:<8} | Avg Time: {avg_time:.3f} ms | "
                      f"Std: {std_time:.3f} ms | Avg Space: {avg_space:.0f} bytes")

    print(f"\nBenchmark completed. Results saved to {output_file}")

# ----------------------------
# Main Entry Point
# ----------------------------

if __name__ == "__main__":
    OUTPUT_CSV = "hash_map_performance_optimized_with_space.csv"
    run_benchmarks(OUTPUT_CSV, base_input=100)
