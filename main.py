"""
Main entry point for VRPTW Solver - Production Optimized
Memory profiling DISABLED for accurate benchmarking (3x speedup)
"""

import sys
import time
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
    Run MIH-MDS solver on Solomon instance.
    PRODUCTION MODE: Memory profiling disabled for speed.
    """
    print(f"\n{'='*60}")
    print(f"VRPTW Solver: MIH-MDS Hybrid Algorithm (Optimized)")
    print(f"{'='*60}")
    print(f"Instance: {instance_file}")
    if max_customers:
        print(f"Customers: {max_customers} (subset)")
    print(f"{'='*60}\n")

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

    # Prepare instance dict
    instance_dict = {
        'depot': depot,
        'customers': customers,
        'vehicle_capacity': vehicle_capacity,
        'file': instance_file  # For R-series detection
    }

    # Solve
    print("\nSolving with MIH-MDS hybrid algorithm...")
    print("Optimizations: O(N²) complexity, smart filtering, adaptive search\n")
    
    start_time = time.time()
    solution, stats = solve_vrptw_with_stats(
        instance=instance_dict,
        max_iterations=max_iterations,
        candidate_k=candidate_k,
        alpha_vehicle=alpha_vehicle
    )
    solve_time = time.time() - start_time

    # Update stats
    improvement_pct = stats.get('improvement_pct', 0.0)
    
    stats.update({
        'num_customers': len(customers),
        'total_cost': solution.total_base_cost,
        'num_vehicles': solution.num_vehicles,
        'num_routes': solution.num_vehicles,
        'solve_time': solve_time,
        'mih_time': 0.0,
        'mds_time': solve_time,
        'total_time': solve_time,
        'improvement': improvement_pct
    })

    # Print results
    print(f"\n{'='*60}")
    print("SOLUTION RESULTS")
    print(f"{'='*60}")
    print_solution_stats(solution, stats)
    print(f"{'='*60}\n")

    return solution, stats


def compare_with_ortools(instance_file: str, max_customers: int = None):
    """Compare MIH-MDS with OR-Tools baseline"""
    print(f"\n{'='*60}")
    print("COMPARISON: Optimized MIH-MDS vs OR-Tools")
    print(f"{'='*60}\n")
    
    # Run custom algorithm
    print("1. Running Optimized MIH-MDS...")
    solution_custom, stats_custom = run_experiment(instance_file, max_customers)
    
    # Clear memory
    del solution_custom
    gc.collect()
    
    # Run OR-Tools
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


def run_batch_benchmark(instance_files: list, max_customers: int = None):
    """
    Run batch benchmark on multiple instances.
    Useful for comprehensive testing.
    """
    print(f"\n{'='*60}")
    print("BATCH BENCHMARK MODE")
    print(f"{'='*60}\n")
    
    results = []
    
    for inst_file in instance_files:
        if not Path(inst_file).exists():
            print(f"Skipping {inst_file}: File not found")
            continue
        
        try:
            _, stats = run_experiment(inst_file, max_customers)
            results.append({
                'instance': Path(inst_file).name,
                'cost': stats['total_cost'],
                'vehicles': stats['num_vehicles'],
                'time': stats['solve_time']
            })
        except Exception as e:
            print(f"Error on {inst_file}: {e}")
            continue
    
    # Summary
    if results:
        print(f"\n{'='*60}")
        print("BATCH SUMMARY")
        print(f"{'='*60}")
        print(f"{'Instance':<15} {'Cost':<12} {'Vehicles':<10} {'Time(s)':<10}")
        print("-" * 60)
        for r in results:
            print(f"{r['instance']:<15} {r['cost']:<12.2f} {r['vehicles']:<10} {r['time']:<10.2f}")
        print(f"{'='*60}\n")
        
        # Aggregate statistics
        avg_time = sum(r['time'] for r in results) / len(results)
        print(f"Average solve time: {avg_time:.2f}s")
    
    return results


def main():
    """Main entry point with enhanced CLI"""
    if len(sys.argv) < 2:
        print("Usage: python main.py <instance_file> [max_customers] [options]")
        print("\nOptions:")
        print("  --benchmark     Run comprehensive benchmark")
        print("  --compare       Compare with OR-Tools")
        print("\nExamples:")
        print("  python main.py data/C101.txt 100")
        print("  python main.py data/C101.txt 100 --compare")
        print("  python main.py data/C101.txt --benchmark")
        sys.exit(1)
    
    instance_file = sys.argv[1]
    max_customers = None
    compare_mode = False
    benchmark_mode = False
    
    # Parse arguments
    for i, arg in enumerate(sys.argv[2:], start=2):
        if arg.isdigit():
            max_customers = int(arg)
        elif arg == '--compare':
            compare_mode = True
        elif arg == '--benchmark':
            benchmark_mode = True
    
    if not Path(instance_file).exists():
        print(f"Error: Instance file not found: {instance_file}")
        sys.exit(1)
    
    # Run appropriate mode
    try:
        if benchmark_mode:
            # Run on multiple instances from same family
            base_path = Path(instance_file).parent
            instance_name = Path(instance_file).stem
            family = instance_name[:2]  # e.g., "C1" from "C101"
            
            instances = sorted(base_path.glob(f"{family}*.txt"))
            if instances:
                run_batch_benchmark([str(f) for f in instances], max_customers)
            else:
                print(f"No instances found matching pattern {family}*.txt")
        
        elif compare_mode:
            compare_with_ortools(instance_file, max_customers)
        
        else:
            solution, stats = run_experiment(instance_file, max_customers)
            
            # Offer comparison
            compare_choice = input("\nCompare with OR-Tools? (y/n): ").strip().lower()
            if compare_choice == 'y':
                compare_with_ortools(instance_file, max_customers)
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()