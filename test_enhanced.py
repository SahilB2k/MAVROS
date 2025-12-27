"""
Test enhanced fleet reduction on C102
"""
import sys
sys.path.insert(0, 'c:/projects/MAVROS')

from core.solomon_loader import load_solomon_subset
from algorithms.hybrid_solver import solve_vrptw_with_stats
import time

print("Testing ENHANCED solver on C102 (100 customers)...")
print("="*60)

depot, customers, vehicle_capacity, _ = load_solomon_subset('data/c102.txt', 100)
instance = {'depot': depot, 'customers': customers, 'vehicle_capacity': vehicle_capacity}

start = time.time()
solution, stats = solve_vrptw_with_stats(instance, max_iterations=120)
elapsed = time.time() - start

print("\n" + "="*60)
print("ENHANCED OPTIMIZATION RESULTS")
print("="*60)
print(f"Cost: {solution.total_base_cost:.2f}")
print(f"Vehicles: {len(solution.routes)}")
print(f"Time: {elapsed:.2f}s")
print(f"Improvement from initial: {stats.get('improvement_pct', 0):.2f}%")
print("="*60)
print("\nTarget: Cost < 1800, Vehicles <= 12 (to match OR-Tools)")
