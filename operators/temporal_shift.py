"""
Temporal Shift Operator - In-place departure time adjustment
HIGHEST PRIORITY operator - cheapest and most effective
Memory: O(1) - modify in place
"""

from typing import Optional, List
from core.data_structures import Route


def temporal_shift_operator_inplace(route: Route, 
                                    temp_arrival_buffer: Optional[List[float]] = None) -> bool:
    """
    Adjust route departure time from depot to minimize waiting time
    
    Strategy:
    1. Find earliest possible departure that maintains feasibility
    2. Try small adjustments around current departure
    3. Select best departure time
    
    Modifies route IN PLACE
    Returns True if improvement was made
    
    Memory: O(1) - no copies created
    """
    if len(route.customer_ids) == 0:
        return False
    
    original_departure = route.departure_time
    original_cost = route.total_cost
    
    # Find earliest feasible departure time
    # This is the time that makes first customer arrive exactly at ready_time
    first_customer = route.get_customer(0)
    from core.data_structures import distance
    travel_time = distance(route.depot, first_customer)
    
    earliest_departure = first_customer.ready_time - travel_time
    earliest_departure = max(0.0, earliest_departure)  # Can't depart before time 0
    
    # Try current departure, earliest departure, and a few in between
    candidates = [
        original_departure,
        earliest_departure,
        (original_departure + earliest_departure) / 2.0,
        earliest_departure + 1.0,
        earliest_departure + 2.0,
    ]
    
    best_departure = original_departure
    best_cost = original_cost
    
    for candidate_departure in candidates:
        if candidate_departure < 0:
            continue
        
        # Try this departure time
        if route.adjust_departure_time_inplace(candidate_departure):
            if route.total_cost < best_cost:
                best_cost = route.total_cost
                best_departure = candidate_departure
    
    # Restore best departure if improvement found
    if best_cost < original_cost:
        route.adjust_departure_time_inplace(best_departure)
        return True
    else:
        # Restore original
        route.adjust_departure_time_inplace(original_departure)
        return False


def optimize_departure_time(route: Route) -> bool:
    """
    Optimize departure time using binary search approach
    More thorough but still O(1) memory
    """
    if len(route.customer_ids) == 0:
        return False
    
    original_departure = route.departure_time
    original_cost = route.total_cost
    
    # Find bounds
    first_customer = route.get_customer(0)
    from core.data_structures import distance
    travel_time = distance(route.depot, first_customer)
    
    earliest = max(0.0, first_customer.ready_time - travel_time)
    latest = original_departure + 50.0  # Reasonable upper bound
    
    # Binary search for best departure
    best_departure = original_departure
    best_cost = original_cost
    
    # Sample points in range
    for i in range(10):
        candidate = earliest + (latest - earliest) * i / 9.0
        
        if route.adjust_departure_time_inplace(candidate):
            if route.total_cost < best_cost:
                best_cost = route.total_cost
                best_departure = candidate
    
    if best_cost < original_cost:
        route.adjust_departure_time_inplace(best_departure)
        return True
    else:
        route.adjust_departure_time_inplace(original_departure)
        return False







