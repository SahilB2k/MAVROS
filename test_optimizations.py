"""
Quick test script to verify optimizations
"""
import sys
sys.path.insert(0, 'c:/projects/MAVROS')

from main import run_experiment

# Test on C101 with 25 customers
print("Testing optimized solver on C101 (25 customers)...")
solution, stats = run_experiment('data/c101.txt', max_customers=25, max_iterations=80)

print("\n" + "="*60)
print("OPTIMIZATION TEST RESULTS")
print("="*60)
print(f"Final Cost: {stats['final_cost']:.2f}")
print(f"Vehicles: {stats['final_vehicles']}")
print(f"Solve Time: {stats['total_time']:.2f}s")
print(f"Improvement: {stats.get('improvement_pct', 0):.2f}%")
print("="*60)
