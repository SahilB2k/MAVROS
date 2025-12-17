"""
Relocate Operator - In-place customer relocation
Memory: O(1) - array splice operation
Now uses candidate list for best-position selection
"""

from typing import Optional, List
from core.data_structures import Route
from operators.candidate_pruning import build_candidate_list_for_customer, get_candidate_insertion_positions


def relocate_operator_inplace(route, temp_buffer, max_relocations=50):
    improved = False
    n = len(route.customer_ids)
    
    # Iterate through each customer to find a better home for them
    for i in range(n):
        best_pos = -1
        # Start with 0 because we only want moves that IMPROVE (delta < 0)
        best_delta = -1e-6 
        
        # Check all possible insertion points j
        for j in range(n + 1):
            # Skip redundant positions (already there)
            if j == i or j == i + 1:
                continue
                
            # Use the high-speed delta function
            delta, feasible = route.get_move_delta_cost(i, i + 1, j)
            
            if feasible and delta < best_delta:
                best_delta = delta
                best_pos = j
        
        # Only perform the physical move if we found an improvement
        if best_pos != -1:
            route.relocate_inplace(i, best_pos)
            # After a physical move, we must update the base cost
            route.calculate_cost_inplace() 
            improved = True
            
    return improved


def best_relocate_inplace(route: Route) -> bool:
    """
    Find best relocation in route (exhaustive but still in-place)
    """
    if len(route.customer_ids) < 2:
        return False
    
    original_cost = route.total_cost
    best_from, best_to = None, None
    best_cost = original_cost
    
    # Try all relocations
    for from_pos in range(len(route.customer_ids)):
        for to_pos in range(len(route.customer_ids)):
            if from_pos == to_pos:
                continue
            
            if route.relocate_inplace(from_pos, to_pos):
                if route.total_cost < best_cost:
                    best_cost = route.total_cost
                    best_from, best_to = from_pos, to_pos
                # Revert
                route.relocate_inplace(to_pos, from_pos)
    
    # Apply best relocation if found
    if best_from is not None and best_cost < original_cost:
        route.relocate_inplace(best_from, best_to)
        return True
    
    return False







