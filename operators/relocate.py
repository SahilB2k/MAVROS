"""
Relocate Operator - In-place customer relocation
Memory: O(1) - array splice operation
"""

from typing import Optional, List
from core.data_structures import Route


def relocate_operator_inplace(route: Route,
                              temp_arrival_buffer: Optional[List[float]] = None,
                              max_relocations: int = 50) -> bool:
    """
    Try relocating customers to different positions in same route
    
    Uses early termination to limit computation
    Modifies route IN PLACE
    Returns True if improvement was made
    
    Memory: O(1) - no copies created
    """
    if len(route.customer_ids) < 2:
        return False
    
    original_cost = route.total_cost
    improved = False
    relocation_count = 0
    
    # Try relocating each customer to each position
    for from_pos in range(len(route.customer_ids)):
        if relocation_count >= max_relocations:
            break
        
        for to_pos in range(len(route.customer_ids)):
            if from_pos == to_pos:
                continue
            
            if relocation_count >= max_relocations:
                break
            
            # Try relocation
            if route.relocate_inplace(from_pos, to_pos):
                if route.total_cost < original_cost:
                    # Improvement found
                    original_cost = route.total_cost
                    improved = True
                    # Continue searching from this improved state
                else:
                    # No improvement, revert
                    route.relocate_inplace(to_pos, from_pos)  # Relocate back
            
            relocation_count += 1
    
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







