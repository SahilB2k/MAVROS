"""
Main entry point for VRPTW Solver
Experiment runner and comparison framework
"""

import sys
import time
import tracemalloc
import gc
from pathlib import Path

from core.solomon_loader import load_solomon_instance, load_solomon_subset
from algorithms.hybrid_solver import solve_vrptw, solve_vrptw_with_stats
from evaluation.performance_metrics import print_solution_stats, compare_solutions


def run_experiment(instance_file: str, max_customers: int = None,
                   max_iterations: int = None,
                   candidate_k: int = 5,
                   alpha_vehicle: float = 1000.0):
    """
    Run MIH-MDS solver on Solomon instance with memory profiling.
    """
    print(f"\n{'='*60}")
    print(f"VRPTW Solver: MIH-MDS Hybrid Algorithm")
    print(f"{'='*60}")
    print(f"Instance: {instance_file}")
    if max_customers:
        print(f"Customers: {max_customers} (subset)")
    print(f"{'='*60}\n")

    # Start memory tracking
    tracemalloc.start()

    # Load instance
    print("Loading instance...")
    start_time = time.time()
    
    if max_customers:
        depot, customers, vehicle_capacity, fleet_size = load_solomon_subset(
            instance_file, max_customers
        )
    else:
        depot, customers, vehicle_capacity, fleet_size = load_solomon_instance(instance_file)
    
    load_time = time.time() - start_time
    print(f"Loaded {len(customers)} customers in {load_time:.3f}s")
    print(f"Vehicle capacity: {vehicle_capacity}")

    # Prepare instance dict for solver
    instance_dict = {
        'depot': depot,
        'customers': customers,
        'vehicle_capacity': vehicle_capacity
    }

    # Solve
    print("\nSolving with MIH-MDS hybrid algorithm...")
    start_time = time.time()
    solution, stats = solve_vrptw_with_stats(
        instance=instance_dict,
        max_iterations=max_iterations,
        candidate_k=candidate_k,
        alpha_vehicle=alpha_vehicle
    )
    solve_time = time.time() - start_time

    # Memory after solving
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    print(f"\nMemory usage:")
    print(f"  Current: {current_mem / 1024 / 1024:.2f} MB")
    print(f"  Peak: {peak_mem / 1024 / 1024:.2f} MB")

    # Merge additional stats with existing stats from solver
    # DO NOT overwrite stats - it already has initial_cost, final_cost, etc.
    # Get improvement_pct before updating (it's already in stats from solver)
    improvement_pct = stats.get('improvement_pct', 0.0)
    
    stats.update({
        'num_customers': len(customers),
        'total_cost': solution.total_base_cost,  # Use actual routing cost, not penalized
        'num_vehicles': solution.num_vehicles,
        'num_routes': solution.num_vehicles,  # Alias for compatibility
        'solve_time': solve_time,
        'mih_time': 0.0,  # Placeholder - not tracked separately
        'mds_time': solve_time,  # Approximate
        'total_time': solve_time,
        'improvement': improvement_pct  # Alias for performance_metrics compatibility
    })

    # Debug: Verify stats keys before passing to print_solution_stats
    print(f"DEBUG: stats keys are {list(stats.keys())}")

    # Print results
    print(f"\n{'='*60}")
    print("SOLUTION RESULTS")
    print(f"{'='*60}")
    print_solution_stats(solution, stats)
    print(f"{'='*60}\n")

    tracemalloc.stop()
    return solution, stats



def compare_with_ortools(instance_file: str, max_customers: int = None):
    """
    Compare MIH-MDS with OR-Tools baseline
    Runs in separate processes to avoid memory conflicts
    """
    print(f"\n{'='*60}")
    print("COMPARISON: MIH-MDS vs OR-Tools")
    print(f"{'='*60}\n")
    
    # Run custom algorithm
    print("1. Running Custom MIH-MDS...")
    solution_custom, stats_custom = run_experiment(instance_file, max_customers)
    
    # Clear memory
    del solution_custom
    gc.collect()
    
    # Run OR-Tools (if available)
    print("\n2. Running OR-Tools baseline...")
    try:
        from baselines.ortools_solver import solve_with_ortools
        stats_ortools = solve_with_ortools(instance_file, max_customers)
        
        print(f"\n{'='*60}")
        print("COMPARISON RESULTS")
        print(f"{'='*60}")
        compare_solutions(stats_custom, stats_ortools)
        print(f"{'='*60}\n")
    except ImportError:
        print("OR-Tools not available. Install with: pip install ortools")
    except Exception as e:
        print(f"OR-Tools error: {e}")
    
    return stats_custom


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python main.py <instance_file> [max_customers]")
        print("\nExample:")
        print("  python main.py data/C101.txt 25")
        print("  python main.py data/C101.txt")
        sys.exit(1)
    
    instance_file = sys.argv[1]
    max_customers = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    if not Path(instance_file).exists():
        print(f"Error: Instance file not found: {instance_file}")
        sys.exit(1)
    
    # Run experiment
    try:
        solution, stats = run_experiment(instance_file, max_customers)
        
        # Optionally compare with OR-Tools
        compare_choice = input("\nCompare with OR-Tools? (y/n): ").strip().lower()
        if compare_choice == 'y':
            compare_with_ortools(instance_file, max_customers)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()







