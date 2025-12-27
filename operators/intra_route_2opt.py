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
    Apply a BEST-IMPROVEMENT 2-opt move within a single route with limited lookahead.
    
    Optimized version:
    - Best-improvement with lookahead limit (check up to 30 moves, take best)
    - Skip obviously infeasible moves early
    - More efficient than pure first-improvement

    Returns:
        True if an improving move was applied, False otherwise.
    """
    n = len(route.customer_ids)
    if n < 3:
        return False

    # Ensure cost/schedule are in sync and use route.total_cost as objective
    route.calculate_cost_inplace()
    old_obj = route.total_cost

    best_improvement = 0.0
    best_move = None
    moves_checked = 0
    max_moves_to_check = 30  # Limited lookahead for speed

    # Try all (i, j) pairs, best-improvement with limited lookahead
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

            # Objective is distance + waiting, which equals total_cost
            new_obj = route.total_cost
            improvement = old_obj - new_obj

            if improvement > best_improvement + 1e-6:
                # Found better move
                best_improvement = improvement
                best_move = (i, j)
                moves_checked += 1
                
                # Early exit if we found a very good move or checked enough
                if best_improvement > 10.0 or moves_checked >= max_moves_to_check:
                    # Roll back this trial
                    left, right = i, j
                    while left < right:
                        route.customer_ids[left], route.customer_ids[right] = (
                            route.customer_ids[right],
                            route.customer_ids[left],
                        )
                        left += 1
                        right -= 1
                    route.calculate_cost_inplace()
                    break

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
        
        if best_move and (best_improvement > 10.0 or moves_checked >= max_moves_to_check):
            break

    # Apply best move if found
    if best_move is not None:
        i, j = best_move
        left, right = i, j
        while left < right:
            route.customer_ids[left], route.customer_ids[right] = (
                route.customer_ids[right],
                route.customer_ids[left],
            )
            left += 1
            right -= 1
        route.calculate_cost_inplace()
        return True

    return False


