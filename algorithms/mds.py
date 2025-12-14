"""
Selective Multi-Directional Search (MDS)
Targeted improvement of critical routes using low-cost, high-impact operators
Memory: O(1) - all operations in-place, reuse temp buffers
"""

from typing import List, Optional
from core.data_structures import Solution, Route
from evaluation.route_analyzer import identify_critical_route_indices
from operators.temporal_shift import temporal_shift_operator_inplace
from operators.swap import swap_operator_inplace
from operators.relocate import relocate_operator_inplace


# Configuration constants
MAX_MDS_ITERATIONS = 50
TOP_N_CRITICAL_ROUTES = 5
MAX_ROUTE_SIZE = 50
EARLY_TERMINATION_THRESHOLD = 10  # Stop if no improvement for N iterations


def selective_mds(solution: Solution,
                  max_iterations: int = MAX_MDS_ITERATIONS,
                  top_n_critical: int = TOP_N_CRITICAL_ROUTES,
                  early_termination: int = EARLY_TERMINATION_THRESHOLD) -> Solution:
    """
    Selective MDS - Improve only critical routes using in-place operators
    
    Strategy:
    1. Identify top N critical routes (lightweight scoring)
    2. Apply operators in priority order (temporal shift > swap > relocate)
    3. All modifications are IN PLACE
    4. Early termination if no improvement
    
    Memory efficient:
    - Single solution object modified in place
    - Reused temp buffers across iterations
    - No route copies created
    
    Args:
        solution: Solution to improve (modified in place)
        max_iterations: Maximum MDS iterations
        top_n_critical: Number of critical routes to improve per iteration
        early_termination: Stop if no improvement for N consecutive iterations
    
    Returns:
        Same solution object (modified in place)
    """
    # Pre-allocate temp buffers (reused across all iterations)
    # Use max route size in solution, but cap at reasonable limit for memory efficiency
    max_route_size = max((len(route.customer_ids) for route in solution.routes), default=0)
    buffer_size = max(MAX_ROUTE_SIZE, max_route_size + 10)  # Add small margin
    temp_arrival_buffer = [0.0] * buffer_size
    
    iteration = 0
    no_improvement_count = 0
    initial_cost = solution.total_cost
    
    while iteration < max_iterations and no_improvement_count < early_termination:
        iteration += 1
        improved_this_iteration = False
        
        # Identify top N critical routes (returns indices only, no copies)
        critical_indices = identify_critical_route_indices(solution, top_n=top_n_critical)
        
        # Try to improve each critical route
        for route_idx in critical_indices:
            route = solution.routes[route_idx]
            
            # Apply operators in priority order (cheapest first)
            # All operators modify route IN PLACE
            
            # 1. Temporal Shift (HIGHEST PRIORITY - cheapest, most effective)
            if temporal_shift_operator_inplace(route, temp_arrival_buffer):
                improved_this_iteration = True
                solution.update_cost()
                continue  # Move to next route after improvement
            
            # 2. Intra-Route Swap
            if swap_operator_inplace(route, temp_arrival_buffer, max_swaps=20):
                improved_this_iteration = True
                solution.update_cost()
                continue  # Move to next route after improvement
            
            # 3. Relocate
            if relocate_operator_inplace(route, temp_arrival_buffer, max_relocations=20):
                improved_this_iteration = True
                solution.update_cost()
        
        # Update improvement tracking
        if improved_this_iteration:
            no_improvement_count = 0
        else:
            no_improvement_count += 1
    
    # Final cost update
    solution.update_cost()
    
    return solution  # Same object, modified in place


def selective_mds_with_route_limit(solution: Solution,
                                   max_iterations: int = MAX_MDS_ITERATIONS,
                                   max_routes_to_improve: int = None) -> Solution:
    """
    Variant that limits number of routes improved per iteration
    Useful for very large instances
    """
    if max_routes_to_improve is None:
        max_routes_to_improve = min(TOP_N_CRITICAL_ROUTES, len(solution.routes))
    
    return selective_mds(solution, max_iterations, top_n_critical=max_routes_to_improve)







