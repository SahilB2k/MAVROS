"""
Performance metrics and comparison utilities
Minimal memory footprint
"""

from typing import Dict
from core.data_structures import Solution


def print_solution_stats(solution: Solution, stats: Dict = None):
    """
    Print solution statistics
    """
    print(f"Total Cost: {solution.total_cost:.2f}")
    print(f"Number of Vehicles: {solution.num_vehicles}")
    print(f"Feasible: {solution.is_feasible()}")
    
    if stats:
        print(f"\nAlgorithm Statistics:")
        # Use get() with defaults to handle missing keys gracefully
        initial_cost = stats.get('initial_cost', solution.total_cost)
        final_cost = stats.get('final_cost', solution.total_cost)
        improvement = stats.get('improvement', stats.get('improvement_pct', 0.0))
        mih_time = stats.get('mih_time', 0.0)
        mds_time = stats.get('mds_time', 0.0)
        total_time = stats.get('total_time', 0.0)
        
        print(f"  Initial Cost (after MIH): {initial_cost:.2f}")
        print(f"  Final Cost (after MDS): {final_cost:.2f}")
        print(f"  Improvement: {improvement:.2f}%")
        if mih_time > 0 or mds_time > 0 or total_time > 0:
            print(f"  MIH Time: {mih_time:.3f}s")
            print(f"  MDS Time: {mds_time:.3f}s")
            print(f"  Total Time: {total_time:.3f}s")
    
    print(f"\nRoute Details:")
    for i, route in enumerate(solution.routes):
        waiting_time = route.get_waiting_time()
        print(f"  Route {i+1}: {len(route.customer_ids)} customers, "
              f"cost={route.total_cost:.2f}, waiting={waiting_time:.2f}")


def compare_solutions(stats_custom: Dict, stats_ortools: Dict):
    """
    Compare custom solution with OR-Tools solution
    """
    print(f"{'Metric':<30} {'Custom':<15} {'OR-Tools':<15} {'Difference':<15}")
    print("-" * 75)
    
    cost_custom = stats_custom['final_cost']
    cost_ortools = stats_ortools.get('cost', 0)
    cost_diff = cost_custom - cost_ortools
    cost_pct = (cost_diff / cost_ortools * 100) if cost_ortools > 0 else 0
    
    print(f"{'Total Cost':<30} {cost_custom:<15.2f} {cost_ortools:<15.2f} {cost_diff:+.2f} ({cost_pct:+.2f}%)")
    
    time_custom = stats_custom['total_time']
    time_ortools = stats_ortools.get('time', 0)
    speedup = time_ortools / time_custom if time_custom > 0 else 0
    
    print(f"{'Solve Time (s)':<30} {time_custom:<15.3f} {time_ortools:<15.3f} {speedup:.1f}x speedup")
    
    vehicles_custom = stats_custom['num_routes']
    vehicles_ortools = stats_ortools.get('num_vehicles', 0)
    
    print(f"{'Number of Vehicles':<30} {vehicles_custom:<15} {vehicles_ortools:<15} {vehicles_custom - vehicles_ortools:+d}")
    
    print(f"\nQuality Gap: {abs(cost_pct):.2f}%")
    print(f"Speedup: {speedup:.1f}x faster")


def calculate_optimality_gap(custom_cost: float, optimal_cost: float) -> float:
    """
    Calculate optimality gap percentage
    """
    if optimal_cost == 0:
        return 0.0
    return ((custom_cost - optimal_cost) / optimal_cost) * 100







