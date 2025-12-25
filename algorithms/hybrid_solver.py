"""
MIH-MDS Hybrid Solver with Multi-Pass Improvement and Coverage Validation.
"""

from typing import Optional, List, Tuple, Dict
import copy
from core.data_structures import Customer, Solution
from algorithms.mih import limited_candidate_mih
from algorithms.mds import selective_mds
from operators.route_merge import merge_underfilled_routes

def solve_vrptw(
    depot: Customer,
    customers: List[Customer],
    vehicle_capacity: int,
    candidate_ratio: float = 0.5,
    min_candidates: int = 5,
    max_mds_iterations: int = 150,
    top_n_critical: int = 10,
    random_seed: Optional[int] = None
) -> Solution:
    """
    Standard wrapper for the hybrid solver to satisfy main.py imports.
    """
    # 1. Construction
    solution = limited_candidate_mih(
        depot=depot,
        customers=customers,
        vehicle_capacity=vehicle_capacity,
        candidate_ratio=candidate_ratio,
        min_candidates=min_candidates,
        random_seed=random_seed
    )

    # 2. Improvement
    solution = selective_mds(
        solution=solution,
        max_iterations=max_mds_iterations,
        top_n_critical=top_n_critical
    )

    return solution

def solve_vrptw_with_stats(instance, max_iterations=None, candidate_k=None, alpha_vehicle=1000.0):
    """
    Enhanced Hybrid Solver with debug checkpoints to track customer loss.
    """
    depot = instance.get('depot')
    customers = instance.get('customers')
    vehicle_capacity = instance.get('vehicle_capacity')
    customers_lookup = {c.id: c for c in customers}
    n = len(customers)
    
    # ------------------------------------------------------------
    # PHASE 1: Initial Construction
    # ------------------------------------------------------------
    solution = limited_candidate_mih(
        depot=depot, 
        customers=customers, 
        vehicle_capacity=vehicle_capacity,
        candidate_ratio=0.5, 
        min_candidates=candidate_k if candidate_k else 5, 
        random_seed=42
    )
    
    # CHECKPOINT 1: Construction Integrity
    mih_count = sum(len(r.customer_ids) for r in solution.routes)
    print(f"DEBUG [Checkpoint 1]: MIH constructed solution with {mih_count}/{n} customers.")

    # Capture Initial Stats (Raw costs)
    initial_cost_raw = sum(route.total_cost for route in solution.routes)
    initial_vehicles = len(solution.routes)

    # ------------------------------------------------------------
    # PHASE 2: Multi-Pass Improvement (MDS)
    # ------------------------------------------------------------
    num_passes = 3 if n <= 50 else 5
    total_iters = max_iterations if max_iterations else 80
    iters_per_pass = total_iters // num_passes

    for pass_num in range(num_passes):
        solution = selective_mds(
            solution=solution,
            max_iterations=iters_per_pass,
            top_n_critical=min(5, len(solution.routes))
        )
        
        # CHECKPOINT 2: MDS Integrity
        mds_count = sum(len(r.customer_ids) for r in solution.routes)
        if mds_count < mih_count:
            print(f"DEBUG [Warning]: MDS pass {pass_num+1} dropped {mih_count - mds_count} customers!")
            mih_count = mds_count # Update tracker

        # Phase 2b: Merge pass with integrity guard
        if pass_num == 0:
            pre_merge_solution = copy.deepcopy(solution)
            try:
                solution = merge_underfilled_routes(
                    solution=solution, 
                    vehicle_capacity=vehicle_capacity,
                    customers_lookup=customers_lookup, 
                    utilization_threshold=0.6
                )
                merge_count = sum(len(r.customer_ids) for r in solution.routes)
                print(f"DEBUG [Checkpoint 3]: Merge pass finished with {merge_count}/{n} customers.")
                if merge_count < n:
                    print("WARNING: Merge reduced customer count; rolling back.")
                    solution = pre_merge_solution
            except Exception as e:
                print(f"WARNING: Merge failed with exception {e}; rolling back.")
                solution = pre_merge_solution

    # ------------------------------------------------------------
    # FINAL VALIDATION & STATS
    # ------------------------------------------------------------
    try:
        solution.validate_coverage(n)
    except Exception as e:
        print(f"WARNING: Coverage validation failed: {e}")
    
    total_served = sum(len(r.customer_ids) for r in solution.routes)
    if total_served < n:
        print(f"\n! WARNING: Integrity Check Failed !")
        print(f"! Served: {total_served}/{n} customers. !")
    else:
        print(f"\n* SUCCESS: All {n}/{n} customers served. *")

    raw_final_cost = sum(route.total_cost for route in solution.routes)
    improvement_pct = ((initial_cost_raw - raw_final_cost) / initial_cost_raw * 100) if initial_cost_raw > 0 else 0
    
    stats = {
        'initial_cost': float(initial_cost_raw),
        'initial_vehicles': int(initial_vehicles),
        'final_cost': float(raw_final_cost),
        'final_vehicles': int(len(solution.routes)),
        'improvement_pct': float(improvement_pct)
    }
    
    return solution, stats