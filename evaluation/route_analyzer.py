"""
Lightweight route criticality scoring
Returns indices only, no route copies
"""

from typing import List, Tuple
from core.data_structures import Route


def calculate_criticality_score(route: Route) -> float:
    """
    Calculate criticality score for a route
    Higher score = more critical (needs improvement)
    
    Factors:
    - Total waiting time
    - Number of tight time windows
    - Average slack
    
    Returns score (higher = more critical)
    Memory: O(1) - calculates on-the-fly, no storage
    """
    if len(route.customer_ids) == 0:
        return 0.0
    
    waiting_time = route.get_waiting_time()
    tight_count = route.get_tight_window_count(slack_threshold=10.0)
    avg_slack = route.get_average_slack()
    
    # Normalize and combine factors
    # Higher waiting time = more critical
    waiting_score = min(waiting_time / 100.0, 1.0)  # Normalize to [0, 1]
    
    # More tight windows = more critical
    tight_score = min(tight_count / 10.0, 1.0)  # Normalize to [0, 1]
    
    # Lower slack = more critical
    slack_score = max(0.0, 1.0 - (avg_slack / 50.0))  # Invert: low slack = high score
    
    # Weighted combination
    score = 0.4 * waiting_score + 0.4 * tight_score + 0.2 * slack_score
    
    return score


def identify_critical_route_indices(solution, top_n: int = 5) -> List[int]:
    """
    Identify top N most critical routes
    
    Returns:
        List of route indices (not route copies)
    
    Memory: O(n) for scores list, but routes are not copied
    """
    scores: List[Tuple[int, float]] = []
    
    for idx, route in enumerate(solution.routes):
        score = calculate_criticality_score(route)
        scores.append((idx, score))
    
    # Sort by score (descending - highest score first)
    scores.sort(key=lambda x: x[1], reverse=True)
    
    # Return top N indices
    return [idx for idx, score in scores[:top_n]]


def is_critical_route(route: Route, 
                     high_waiting_threshold: float = 50.0,
                     tight_window_threshold: int = 3,
                     low_slack_threshold: float = 20.0) -> bool:
    """
    Check if route meets criticality criteria
    
    Returns True if route is critical (needs improvement)
    """
    waiting_time = route.get_waiting_time()
    tight_count = route.get_tight_window_count(slack_threshold=10.0)
    avg_slack = route.get_average_slack()
    
    return (waiting_time > high_waiting_threshold or
            tight_count > tight_window_threshold or
            avg_slack < low_slack_threshold)







