"""
Intra-Route Swap Operator - In-place customer swap
Memory: O(1) - swap indices in place
"""

from typing import Optional, List
from core.data_structures import Route


def swap_operator_inplace(route: Route,
                         temp_arrival_buffer: Optional[List[float]] = None,
                         max_swaps: int = 50) -> bool:
    """
    Try swapping pairs of customers within same route
    
    Uses early termination to limit computation
    Modifies route IN PLACE
    Returns True if improvement was made
    
    Memory: O(1) - no copies created
    """
    if len(route.customer_ids) < 2:
        return False
    
    original_cost = route.total_cost
    improved = False
    swap_count = 0
    
    # Try swapping pairs (with early termination)
    for i in range(len(route.customer_ids)):
        if swap_count >= max_swaps:
            break
        
        for j in range(i + 1, len(route.customer_ids)):
            if swap_count >= max_swaps:
                break
            
            # Try swap
            if route.swap_inplace(i, j):
                if route.total_cost < original_cost:
                    # Improvement found
                    original_cost = route.total_cost
                    improved = True
                    # Continue searching from this improved state
                else:
                    # No improvement, revert
                    route.swap_inplace(i, j)  # Swap back
            
            swap_count += 1
    
    return improved


def best_swap_inplace(route: Route) -> bool:
    """
    Find best swap in route (exhaustive but still in-place)
    """
    if len(route.customer_ids) < 2:
        return False
    
    original_cost = route.total_cost
    best_i, best_j = None, None
    best_cost = original_cost
    
    # Try all pairs
    for i in range(len(route.customer_ids)):
        for j in range(i + 1, len(route.customer_ids)):
            if route.swap_inplace(i, j):
                if route.total_cost < best_cost:
                    best_cost = route.total_cost
                    best_i, best_j = i, j
                # Revert
                route.swap_inplace(i, j)
    
    # Apply best swap if found
    if best_i is not None and best_cost < original_cost:
        route.swap_inplace(best_i, best_j)
        return True
    
    return False







