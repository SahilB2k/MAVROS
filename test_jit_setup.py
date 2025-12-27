
import numpy as np
import time
from numba import jit
from operators.jit_kernels import evaluate_route_jit

# Dummy data
route = np.array([1, 2, 3], dtype=np.int32)
# [id, x, y, demand, ready, due, service]
customers = np.zeros((5, 7), dtype=np.float64)
customers[1] = [1, 10, 10, 10, 0, 100, 10]
customers[2] = [2, 20, 20, 10, 0, 100, 10]
customers[3] = [3, 30, 30, 10, 0, 100, 10]
depot = np.array([0, 0, 0, 0, 0, 1000, 0], dtype=np.float64)
capacity = 100

# Compile
print("Compiling...")
evaluate_route_jit(route, customers, depot, capacity)

# Benchmark
print("Running Benchmark...")
start = time.time()
iterations = 50000
for _ in range(iterations):
    evaluate_route_jit(route, customers, depot, capacity)
end = time.time()

avg_us = (end - start) / iterations * 1e6
print(f"RESULT: {avg_us:.2f} microseconds per call")
