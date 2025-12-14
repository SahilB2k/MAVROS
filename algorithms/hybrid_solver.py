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


def solve_vrptw_with_stats(
    depot: Customer,
    customers: List[Customer],
    vehicle_capacity: int,
    **kwargs
) -> Tuple[Solution, Dict]:
    """
    Solve VRPTW and return solution with statistics
    
    Returns:
        (solution, stats_dict)
        stats_dict contains:
        - initial_cost: Cost after MIH
        - final_cost: Cost after MDS
        - improvement: Percentage improvement
        - num_routes: Number of vehicles used
        - is_feasible: Feasibility flag
    """
    import time
    
    # Phase 1: MIH
    start_time = time.time()
    solution = limited_candidate_mih(
        depot=depot,
        customers=customers,
        vehicle_capacity=vehicle_capacity,
        candidate_ratio=kwargs.get('candidate_ratio', CANDIDATE_RATIO),
        min_candidates=kwargs.get('min_candidates', MIN_CANDIDATES),
        random_seed=kwargs.get('random_seed', None)
    )
    mih_time = time.time() - start_time
    initial_cost = solution.total_cost
    
    # Phase 2: MDS
    start_time = time.time()
    solution = selective_mds(
        solution=solution,
        max_iterations=kwargs.get('max_mds_iterations', MAX_MDS_ITERATIONS),
        top_n_critical=kwargs.get('top_n_critical', TOP_N_CRITICAL_ROUTES)
    )
    mds_time = time.time() - start_time
    final_cost = solution.total_cost
    
    stats = {
        'initial_cost': initial_cost,
        'final_cost': final_cost,
        'improvement': ((initial_cost - final_cost) / initial_cost * 100) if initial_cost > 0 else 0.0,
        'num_routes': solution.num_vehicles,
        'is_feasible': solution.is_feasible(),
        'mih_time': mih_time,
        'mds_time': mds_time,
        'total_time': mih_time + mds_time
    }
    
    return solution, stats







