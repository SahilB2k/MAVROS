"""
MIH-MDS Hybrid Solver
Combines Limited Candidate MIH with Selective MDS
Single solution object maintained throughout
"""

from typing import Optional, List, Tuple, Dict
from core.data_structures import Customer, Solution
from algorithms.mih import limited_candidate_mih
from algorithms.mds import selective_mds


# Configuration
CANDIDATE_RATIO = 0.3  # Sample 30% of candidates in MIH
MIN_CANDIDATES = 3
MAX_MDS_ITERATIONS = 50
TOP_N_CRITICAL_ROUTES = 5


def solve_vrptw(
    depot: Customer,
    customers: list[Customer],
    vehicle_capacity: int,
    candidate_ratio: float = CANDIDATE_RATIO,
    min_candidates: int = MIN_CANDIDATES,
    max_mds_iterations: int = MAX_MDS_ITERATIONS,
    top_n_critical: int = TOP_N_CRITICAL_ROUTES,
    random_seed: Optional[int] = None
) -> Solution:
    """
    Solve VRPTW using MIH-MDS hybrid algorithm
    
    Phase 1: Limited Candidate MIH (intentionally sub-optimal)
    Phase 2: Selective MDS (targeted improvement)
    
    Memory efficient:
    - Single solution object throughout
    - All modifications in place
    - No distance matrix caching
    - Minimal temporary objects
    
    Args:
        depot: Depot customer
        customers: List of customer objects
        vehicle_capacity: Vehicle capacity constraint
        candidate_ratio: Fraction of candidates to sample in MIH (0.3 = 30%)
        min_candidates: Minimum candidates to always check
        max_mds_iterations: Maximum MDS improvement iterations
        top_n_critical: Number of critical routes to improve per MDS iteration
        random_seed: Random seed for reproducibility
    
    Returns:
        Solution object (feasible VRPTW solution)
    """
    # Phase 1: Limited Candidate MIH
    # Generates fast, feasible, but improvable solution
    solution = limited_candidate_mih(
        depot=depot,
        customers=customers,
        vehicle_capacity=vehicle_capacity,
        candidate_ratio=candidate_ratio,
        min_candidates=min_candidates,
        random_seed=random_seed
    )
    
    # Phase 2: Selective MDS
    # Improves critical routes using in-place operators
    solution = selective_mds(
        solution=solution,
        max_iterations=max_mds_iterations,
        top_n_critical=top_n_critical
    )
    
    return solution


def solve_vrptw_with_stats(instance, max_iterations=None, candidate_k=None, alpha_vehicle=1000.0):
    from algorithms.mih import limited_candidate_mih
    from algorithms.mds import selective_mds
    from operators.route_merge import merge_underfilled_routes
    
    depot = instance.get('depot')
    customers = instance.get('customers')
    vehicle_capacity = instance.get('vehicle_capacity')
    customers_lookup = {c.id: c for c in customers}
    n = len(customers)
    
    # Adaptive iterations
    if max_iterations is None:
        max_iterations = n * 2 if n <= 100 else n
    num_passes = 2
    
    # PHASE 1: Initial solution
    solution = limited_candidate_mih(
        depot=depot, customers=customers, vehicle_capacity=vehicle_capacity,
        candidate_ratio=0.3, min_candidates=3, random_seed=42
    )
    
    solution.update_cost(alpha_vehicle=alpha_vehicle)
    # CAPTURE INITIAL VALUES (raw cost without penalty for fair comparison)
    initial_cost_fixed = float(sum(route.total_cost for route in solution.routes))
    initial_vehicles_fixed = int(solution.num_vehicles)
    
    # PHASE 2: Improvement (multiple passes for quality)
    # Use 3-5 passes depending on instance size
    num_passes = 3 if n <= 50 else (4 if n <= 100 else 5)
    base_iterations = max_iterations // num_passes
    
    for pass_num in range(num_passes):
        solution = selective_mds(
            solution=solution,
            max_iterations=base_iterations,
            top_n_critical=min(2 if n > 50 else 5, len(solution.routes)),
            early_termination=20  # Increased from 5 to 20 for deeper local search
        )
        solution.update_cost(alpha_vehicle=alpha_vehicle)
        
        if pass_num == 0 and len(solution.routes) > 1:
            solution = merge_underfilled_routes(
                solution=solution, vehicle_capacity=vehicle_capacity,
                customers_lookup=customers_lookup, utilization_threshold=0.5
            )
            solution.update_cost(alpha_vehicle=alpha_vehicle)
    
    # FINAL STATS
    # Calculate raw cost (distance + waiting) without vehicle penalty for fair comparison
    # This is the actual travel cost, not the penalized objective
    raw_final_cost = sum(route.total_cost for route in solution.routes)
    
    # Also calculate initial raw cost for comparison
    solution.update_cost(alpha_vehicle=alpha_vehicle)  # Update penalized cost for internal use
    final_vehicles = int(solution.num_vehicles)
    
    # Calculate improvement percentage using raw costs
    improvement_pct = ((initial_cost_fixed - raw_final_cost) / initial_cost_fixed * 100) if initial_cost_fixed > 0 else 0.0
    
    stats = {
        'initial_cost': float(initial_cost_fixed),
        'initial_vehicles': int(initial_vehicles_fixed),
        'final_cost': float(raw_final_cost),  # Raw cost without penalty
        'final_vehicles': int(final_vehicles),
        'improvement_pct': float(improvement_pct)
    }
    
    return solution, stats