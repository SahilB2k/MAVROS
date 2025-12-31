"""
Fast Hybrid Solver with Aggressive Fleet Reduction
Target: Beat OR-Tools on cost, vehicles, and speed
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
    solution = limited_candidate_mih(
        depot=depot,
        customers=customers,
        vehicle_capacity=vehicle_capacity,
        candidate_ratio=candidate_ratio,
        min_candidates=min_candidates,
        random_seed=random_seed
    )

    solution = selective_mds(
        solution=solution,
        max_iterations=max_mds_iterations,
        top_n_critical=top_n_critical
    )

    return solution

def solve_vrptw_with_stats(instance, max_iterations=None, candidate_k=None, alpha_vehicle=1000.0):
    """
    Fast Hybrid Solver with 3-phase optimization
    """
    depot = instance.get('depot')
    customers = instance.get('customers')
    vehicle_capacity = instance.get('vehicle_capacity')
    customers_lookup = {c.id: c for c in customers}
    n = len(customers)
    
    # ===== PHASE 1: Fast Construction =====
    print(f"\n{'='*60}")
    print(f"PHASE 1: Fast Construction (Parallel Savings)")
    print(f"{'='*60}")
    
    solution = limited_candidate_mih(
        depot=depot, 
        customers=customers, 
        vehicle_capacity=vehicle_capacity,
        candidate_ratio=0.5, 
        min_candidates=candidate_k if candidate_k else 5, 
        random_seed=42
    )
    
    mih_count = sum(len(r.customer_ids) for r in solution.routes)
    print(f"Construction: {len(solution.routes)} routes, {mih_count}/{n} customers")
    
    initial_cost_raw = sum(route.total_cost for route in solution.routes)
    initial_vehicles = len(solution.routes)
    
    # ===== PHASE 2: Fast Route Consolidation =====
    print(f"\n{'='*60}")
    print(f"PHASE 2: Route Consolidation")
    print(f"{'='*60}")
    
    # Aggressive merging (multiple passes with different thresholds)
    for threshold in [0.8, 0.6, 0.4]:
        pre_merge = len(solution.routes)
        solution = merge_underfilled_routes(
            solution=solution, 
            vehicle_capacity=vehicle_capacity,
            customers_lookup=customers_lookup, 
            utilization_threshold=threshold
        )
        post_merge = len(solution.routes)
        if post_merge < pre_merge:
            print(f"  Merge (threshold={threshold:.1f}): {pre_merge} → {post_merge} routes")
    
    # ===== PHASE 3: Fast Optimization =====
    print(f"\n{'='*60}")
    print(f"PHASE 3: Fast Multi-Directional Search")
    print(f"{'='*60}")
    
    # Adaptive iteration budget based on problem size
    if max_iterations:
        total_iters = max_iterations
    else:
        total_iters = 100 if n <= 50 else 150 if n <= 100 else 200
    
    solution = selective_mds(
        solution=solution,
        max_iterations=total_iters,
        top_n_critical=min(3, len(solution.routes))
    )
    
    # ===== PHASE 4: Final Polishing =====
    print(f"\n{'='*60}")
    print(f"PHASE 4: Final Polishing")
    print(f"{'='*60}")
    
    # One more merge pass
    pre_final = len(solution.routes)
    solution = merge_underfilled_routes(
        solution=solution, 
        vehicle_capacity=vehicle_capacity,
        customers_lookup=customers_lookup, 
        utilization_threshold=0.3
    )
    if len(solution.routes) < pre_final:
        print(f"  Final merge: {pre_final} → {len(solution.routes)} routes")
    
    # ===== VALIDATION & STATS =====
    try:
        solution.validate_coverage(n)
    except Exception as e:
        print(f"WARNING: Coverage validation failed: {e}")
    
    total_served = sum(len(r.customer_ids) for r in solution.routes)
    if total_served < n:
        print(f"\n! WARNING: Integrity Check Failed !")
        print(f"! Served: {total_served}/{n} customers. !")
    else:
        print(f"\n✓ SUCCESS: All {n}/{n} customers served.")

    raw_final_cost = sum(route.total_cost for route in solution.routes)
    
    # Vehicle penalty for comparison
    vehicle_penalty = len(solution.routes) * 300
    penalized_cost = raw_final_cost + vehicle_penalty
    
    # Safety checks
    if raw_final_cost == float('inf'):
        print(f"WARNING: Final cost is inf, setting to 1,000,000 for metrics")
        raw_final_cost = 1000000.0
        penalized_cost = 1000000.0
    
    if initial_cost_raw == float('inf'):
        initial_cost_raw = 1000000.0
    
    improvement_pct = ((initial_cost_raw - raw_final_cost) / initial_cost_raw * 100) if initial_cost_raw > 0 else 0
    
    print(f"\n{'='*60}")
    print(f"FINAL SOLUTION SUMMARY")
    print(f"{'='*60}")
    print(f"  Distance Cost:      {raw_final_cost:.2f}")
    print(f"  Vehicle Penalty:    {vehicle_penalty:.2f} ({len(solution.routes)} × 300)")
    print(f"  Total Penalized:    {penalized_cost:.2f}")
    print(f"  Vehicles:           {len(solution.routes)}")
    print(f"  Improvement:        {improvement_pct:.2f}%")
    
    # Route statistics
    route_sizes = [len(r.customer_ids) for r in solution.routes]
    route_loads = [r.current_load for r in solution.routes]
    utilizations = [load / vehicle_capacity * 100 for load in route_loads]
    
    print(f"\n  Route Statistics:")
    print(f"    Size:  min={min(route_sizes)}, max={max(route_sizes)}, avg={sum(route_sizes)/len(route_sizes):.1f}")
    print(f"    Load:  min={min(route_loads)}, max={max(route_loads)}, avg={sum(route_loads)/len(route_loads):.1f}")
    print(f"    Util:  min={min(utilizations):.1f}%, max={max(utilizations):.1f}%, avg={sum(utilizations)/len(utilizations):.1f}%")
    print(f"{'='*60}\n")
    
    stats = {
        'initial_cost': float(initial_cost_raw),
        'initial_vehicles': int(initial_vehicles),
        'final_cost': float(raw_final_cost),
        'final_vehicles': int(len(solution.routes)),
        'improvement_pct': float(improvement_pct),
        'penalized_cost': float(penalized_cost)
    }
    
    return solution, stats