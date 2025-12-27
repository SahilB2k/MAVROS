"""
Verification script for balanced solver improvements
Checks C101.25 performance against targets
"""
import time
from core.solomon_loader import load_solomon_subset
from algorithms.hybrid_solver import solve_vrptw_with_stats

# Test on C101 with 25 customers
instance_file = "data/c101.txt"
max_customers = 25

print("="*60)
print("VERIFY IMPROVEMENTS - C101 (25 customers)")
print("Target: 3 vehicles, Cost ~191.3")
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
    max_iterations=120, # Increased slightly
    candidate_k=5,
    alpha_vehicle=1000.0
)
solve_time = time.time() - start_time

print("\n" + "="*60)
print("RESULTS")
print("="*60)
print(f"Vehicles: {len(solution.routes)}")
print(f"Total Cost: {solution.total_base_cost:.2f}")
print(f"Solve Time: {solve_time:.3f}s")
print(f"Feasible: {solution.is_feasible()}")
print(f"Initial Cost: {stats['initial_cost']:.2f}")
print(f"Final Cost: {stats['final_cost']:.2f}")
print(f"Improvement: {stats['improvement_pct']:.2f}%")
print("="*60)

# Validation
optimal_cost = 191.3
gap = ((solution.total_base_cost - optimal_cost) / optimal_cost) * 100
print(f"Optimality Gap: {gap:.2f}%")

if len(solution.routes) <= 3 and gap < 5.0:
    print("SUCCESS: Met targets!")
elif len(solution.routes) <= 3:
    print("PARTIAL SUCCESS: Met vehicle target but cost gap is high.")
else:
    print("FAILURE: Did not meet vehicle target.")
