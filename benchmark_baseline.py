"""
Baseline Benchmark Script
- Establishes a performance baseline for a small instance (C101.25).
- Useful for quick regression testing before running full benchmarks.
"""
import time
from core.solomon_loader import load_solomon_subset
from algorithms.hybrid_solver import solve_vrptw_with_stats

# Test on C101 with 25 customers
instance_file = "data/c101.txt"
max_customers = 25

print("="*60)
print("BASELINE BENCHMARK - C101 (25 customers)")
print("="*60)

# Load instance
depot, customers, vehicle_capacity, fleet_size = load_solomon_subset(
    instance_file, max_customers
)

instance_dict = {
    'depot': depot,
    'customers': customers,
    'vehicle_capacity': vehicle_capacity
}

# Run solver
start_time = time.time()
solution, stats = solve_vrptw_with_stats(
    instance=instance_dict,
    max_iterations=100,
    candidate_k=5,
    alpha_vehicle=1000.0
)
solve_time = time.time() - start_time

print("\n" + "="*60)
print("BASELINE RESULTS")
print("="*60)
print(f"Vehicles: {len(solution.routes)}")
print(f"Total Cost: {solution.total_base_cost:.2f}")
print(f"Solve Time: {solve_time:.3f}s")
print(f"Feasible: {solution.is_feasible()}")
print(f"Initial Cost: {stats['initial_cost']:.2f}")
print(f"Final Cost: {stats['final_cost']:.2f}")
print(f"Improvement: {stats['improvement_pct']:.2f}%")
print("="*60)

# Expected OR-Tools results for comparison
print("\nOR-Tools Expected (approximate):")
print("  Vehicles: ~12")
print("  Total Cost: ~191-200")
print("  Solve Time: ~1-3s")
