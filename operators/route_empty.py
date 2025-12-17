"""
Route Emptying Operator
Attempts to relocate all customers from the smallest route into other routes,
then removes the empty route to reduce vehicle count.
"""

from core.data_structures import Solution, Route
from operators.candidate_pruning import build_candidate_list_for_customer, get_candidate_insertion_positions


def route_empty_inplace(solution) -> bool:
    """
    Identifies the smallest route and tries to move ALL its customers 
    to other existing routes. Returns True only if the route is successfully 
    deleted (emptied).
    """
    if len(solution.routes) <= 1:
        return False

    # 1. Find the smallest route with < 6 customers
    # We sort by length so we always try to kill the easiest one first
    routes_by_size = sorted(
        [r for r in solution.routes if 0 < len(r.customer_ids) < 6],
        key=lambda r: len(r.customer_ids)
    )

    for target_route in routes_by_size:
        target_idx = solution.routes.index(target_route)
        customers_to_move = list(target_route.customer_ids)
        successful_relocations = 0

        # Store a snapshot to rollback if we can't move EVERYONE
        # (Since we are doing this in-place, we must be careful)
        
        moves_to_execute = [] # List of (customer_id, destination_route_idx, position)

        for cust_id in customers_to_move:
            found_home = False
            # Try to find a home in ANY other route
            for other_idx, other_route in enumerate(solution.routes):
                if other_idx == target_idx:
                    continue
                
                # Check every insertion position in the other route
                for pos in range(len(other_route.customer_ids) + 1):
                    # Check feasibility and cost delta
                    delta, feasible = other_route.get_move_delta_cost_for_external_customer(cust_id, pos)
                    
                    if feasible:
                        moves_to_execute.append((cust_id, other_idx, pos))
                        found_home = True
                        break
                if found_home:
                    break
            
            if not found_home:
                # Can't find a home for this customer -> abort entire operation
                moves_to_execute = []
                break
        
        # 2. If we found a home for EVERY customer, execute ALL moves atomically
        if len(moves_to_execute) == len(customers_to_move):
            # Backup state in case any insertion fails
            backup_routes = []
            for r in solution.routes:
                backup_routes.append({
                    'ids': list(r.customer_ids),
                    'arrivals': list(r.arrival_times),
                    'load': r.current_load
                })
            
            # Try to execute all insertions
            all_insertions_succeeded = True
            for cust_id, dest_idx, pos in moves_to_execute:
                if not solution.routes[dest_idx].insert_inplace(cust_id, pos):
                    # Insertion failed -> rollback all previous insertions
                    all_insertions_succeeded = False
                    # Restore all routes to backup state
                    for i, r in enumerate(solution.routes):
                        r.customer_ids = backup_routes[i]['ids']
                        r.arrival_times = backup_routes[i]['arrivals']
                        r.current_load = backup_routes[i]['load']
                        r._recalculate_from(0)
                        r.calculate_cost_inplace()
                    break
            
            if all_insertions_succeeded:
                # All insertions succeeded -> remove the now-empty route
                solution.routes.pop(target_idx)
                return True

    return False

