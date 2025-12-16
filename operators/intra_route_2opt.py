"""
Intra-route 2-opt operator (FIRST-IMPROVEMENT).

Operates IN PLACE on a Route:
- Considers all (i, j) pairs with 0 <= i < j < n
- Reverses segment customer_ids[i:j+1]
- Recomputes schedule/cost using existing Route methods
- Enforces time-window feasibility
- Accepts first move with improved (distance + waiting)
"""

from core.data_structures import Route


def intra_route_2opt_inplace(route: Route) -> bool:
    """
    Apply a FIRST-IMPROVEMENT 2-opt move within a single route.

    Returns:
        True if an improving move was applied, False otherwise.
    """
    n = len(route.customer_ids)
    if n < 3:
        return False

    # Ensure cost/schedule are in sync
    route.calculate_cost_inplace()
    old_distance = route.get_total_distance()
    old_waiting = route.get_waiting_time()
    old_obj = old_distance + old_waiting

    # Try all (i, j) pairs, first-improvement
    for i in range(n - 2):
        for j in range(i + 1, n):
            # In-place segment reversal [i, j]
            left, right = i, j
            while left < right:
                route.customer_ids[left], route.customer_ids[right] = (
                    route.customer_ids[right],
                    route.customer_ids[left],
                )
                left += 1
                right -= 1

            # Recompute schedule/cost and check feasibility
            route.calculate_cost_inplace()

            if not route.is_feasible():
                # Roll back change (reverse the same segment again)
                left, right = i, j
                while left < right:
                    route.customer_ids[left], route.customer_ids[right] = (
                        route.customer_ids[right],
                        route.customer_ids[left],
                    )
                    left += 1
                    right -= 1
                route.calculate_cost_inplace()
                continue

            new_distance = route.get_total_distance()
            new_waiting = route.get_waiting_time()
            new_obj = new_distance + new_waiting

            if new_obj < old_obj - 1e-6:
                # First improving move accepted
                return True

            # Not improving: roll back
            left, right = i, j
            while left < right:
                route.customer_ids[left], route.customer_ids[right] = (
                    route.customer_ids[right],
                    route.customer_ids[left],
                )
                left += 1
                right -= 1
            route.calculate_cost_inplace()

    return False


