"""
Distance-based candidate pruning utilities
Builds nearest neighbor lists for efficient insertion evaluation
"""

from typing import Dict, List
from core.data_structures import Route, Customer, distance


def build_candidate_list_for_customer(customer: Customer, 
                                      all_customers: List[Customer],
                                      k: int = 25) -> List[int]:
    """
    Build a list of k nearest neighbor customer IDs for a given customer.
    Used for candidate pruning in insertion operations.
    """
    distances = []
    for other in all_customers:
        if other.id == customer.id:
            continue
        dist = distance(customer, other)
        distances.append((other.id, dist))
    
    # Sort by distance and take k nearest
    distances.sort(key=lambda x: x[1])
    return [other_id for other_id, _ in distances[:k]]


def get_candidate_insertion_positions(route: Route, 
                                     customer: Customer,
                                     candidate_neighbors: List[int],
                                     k: int = 25) -> List[int]:
    """
    Return insertion positions in route where the predecessor is among
    the k nearest neighbors of the customer being inserted.
    
    This prunes the search space from O(N) to O(k) positions.
    """
    if len(route.customer_ids) == 0:
        return [0]  # Only one position for empty route
    
    candidate_positions = []
    
    # Always consider position 0 (depot as predecessor)
    candidate_positions.append(0)
    
    # Check each position where predecessor is a nearest neighbor
    for pos in range(1, len(route.customer_ids) + 1):
        prev_id = route.customer_ids[pos - 1]
        if prev_id in candidate_neighbors:
            candidate_positions.append(pos)
    
    # If we have very few candidates, add a few more positions to ensure feasibility
    if len(candidate_positions) < 3 and len(route.customer_ids) > 0:
        # Add positions near the beginning and end
        if len(route.customer_ids) > 0:
            candidate_positions.append(min(2, len(route.customer_ids)))
        if len(route.customer_ids) > 1:
            candidate_positions.append(max(0, len(route.customer_ids) - 1))
        candidate_positions.append(len(route.customer_ids))  # End position
    
    # Remove duplicates and sort
    return sorted(list(set(candidate_positions)))

