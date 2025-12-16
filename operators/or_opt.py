"""
Intra-route Or-Opt (1-3 customer segment relocate) - FIRST IMPROVEMENT.

Moves a short segment within the same route to another position,
keeping feasibility. Objective: distance + waiting.
"""

from core.data_structures import Route


def or_opt_inplace(route: Route, max_segment_len: int = 3) -> bool:
    """
    Apply a FIRST-IMPROVEMENT or-opt (segment relocate) within a route.

    Args:
        route: Route to modify in place.
        max_segment_len: maximum segment length to move (1..3 typical).

    Returns:
        True if an improving move was applied; False otherwise.
    """
    n = len(route.customer_ids)
    if n < 3:
        return False

    route.calculate_cost_inplace()
    base_dist = route.get_total_distance()
    base_wait = route.get_waiting_time()
    base_obj = base_dist + base_wait

    # Try segment lengths 1..max_segment_len
    for seg_len in range(1, min(max_segment_len, n) + 1):
        for start in range(0, n - seg_len + 1):
            end = start + seg_len  # exclusive
            segment = route.customer_ids[start:end]

            # Remove segment
            removed = route.customer_ids[start:end]
            del route.customer_ids[start:end]

            for insert_pos in range(0, len(route.customer_ids) + 1):
                # Skip no-op positions (same place)
                if insert_pos == start:
                    continue
                # Insert segment
                route.customer_ids[insert_pos:insert_pos] = segment

                # Recompute schedule/cost and check feasibility
                route.calculate_cost_inplace()
                if route.is_feasible():
                    new_obj = route.get_total_distance() + route.get_waiting_time()
                    if new_obj < base_obj - 1e-6:
                        return True

                # Rollback insert
                del route.customer_ids[insert_pos:insert_pos + seg_len]
                route.customer_ids[start:start] = removed
                route.calculate_cost_inplace()

            # Ensure route restored for next start
            # (already restored in rollback loop)

    return False


