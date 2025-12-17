"""
Lightweight destroy-and-repair (LNS-style) to escape local minima.

Strategy:
- Destroy: remove a subset of customers from the most critical routes.
- Repair: reinsert customers greedily where the penalised objective improves.

All operations are IN PLACE; uses Route.insert_inplace for feasibility.
"""

import random
from typing import List
from core.data_structures import Solution, Route, Customer
from evaluation.route_analyzer import identify_critical_route_indices


def _calculate_insertion_cost(route: Route, customer_id: int, position: int) -> float:
    """
    Calculate insertion cost: Added Distance + 2 * Added Waiting Time
    Returns float('inf') if insertion is infeasible.
    """
    customer = route.customers_lookup[customer_id]
    
    # Capacity check
    if route.current_load + customer.demand > route.vehicle_capacity:
        return float('inf')
    
    # Calculate cost before insertion
    old_cost = route.total_cost
    old_distance = route.get_total_distance()
    old_waiting = old_cost - old_distance
    
    # Try insertion
    if not route.insert_inplace(customer_id, position):
        return float('inf')
    
    # Calculate cost after insertion
    new_cost = route.total_cost
    new_distance = route.get_total_distance()
    new_waiting = new_cost - new_distance
    
    # Calculate deltas
    delta_distance = new_distance - old_distance
    delta_waiting = new_waiting - old_waiting
    
    # Rollback
    route.customer_ids.pop(position)
    route.arrival_times.pop(position)
    route.current_load -= customer.demand
    route._recalculate_from(position)
    route.calculate_cost_inplace()
    
    # Cost = Added Distance + 2 * Added Waiting Time
    return delta_distance + (2.0 * delta_waiting)


def _try_insert_customer_best_fit(route: Route, customer_id: int) -> bool:
    """
    Best-fit greedy insertion that minimizes (Added Distance + 2 * Added Waiting Time).
    Returns True if inserted.
    """
    best_pos = None
    best_cost = float('inf')

    for pos in range(len(route.customer_ids) + 1):
        cost = _calculate_insertion_cost(route, customer_id, pos)
        if cost < best_cost:
            best_cost = cost
            best_pos = pos

    if best_pos is None or best_cost == float('inf'):
        return False

    return route.insert_inplace(customer_id, best_pos)


def _related_removal(solution: Solution, 
                    removal_fraction: float = 0.25,
                    fixed_remove_count: int = None,
                    random_seed: int = 42) -> List[int]:
    """
    Related removal: Remove clusters of customers based on distance/time proximity.
    Uses a seed customer and expands to nearby customers.
    """
    import random
    from core.data_structures import distance
    
    random.seed(random_seed)
    routes = solution.routes
    
    # Collect all customers with their positions
    all_customers = []
    for route in routes:
        for cid in route.customer_ids:
            all_customers.append(cid)
    
    if len(all_customers) == 0:
        return []
    
    # Determine removal count
    if fixed_remove_count is not None:
        remove_count = min(fixed_remove_count, len(all_customers))
    else:
        remove_count = max(5, int(len(all_customers) * removal_fraction))
        remove_count = min(remove_count, len(all_customers))
    
    if remove_count == 0:
        return []
    
    # Start with a random seed customer
    seed_customer_id = random.choice(all_customers)
    seed_customer = routes[0].customers_lookup[seed_customer_id]
    
    to_remove = [seed_customer_id]
    remaining = [cid for cid in all_customers if cid != seed_customer_id]
    
    # Expand cluster by adding nearest neighbors
    while len(to_remove) < remove_count and remaining:
        # Find nearest unremoved customer to any removed customer
        min_dist = float('inf')
        nearest_id = None
        
        for removed_id in to_remove:
            removed_customer = routes[0].customers_lookup[removed_id]
            for candidate_id in remaining:
                candidate = routes[0].customers_lookup[candidate_id]
                dist = distance(removed_customer, candidate)
                if dist < min_dist:
                    min_dist = dist
                    nearest_id = candidate_id
        
        if nearest_id is None:
            break
        
        to_remove.append(nearest_id)
        remaining.remove(nearest_id)
    
    return to_remove


def lns_destroy_repair(solution: Solution,
                      removal_fraction: float = 0.15,
                      fixed_remove_count: int = None,
                      random_seed: int = 42) -> bool:
    """
    Enhanced LNS with related removal and best-fit greedy repair.
    Destroy: Remove 15-20% of customers using related removal (distance/time clusters).
    Repair: Reinsert using best-fit greedy that minimizes (Distance + 2 * Waiting Time).
    Returns True if the solution improved (penalised objective decreased).
    """
    if not solution.routes:
        return False

    solution.update_cost()
    current_obj = solution.total_cost

    # Related removal: remove clusters of nearby customers
    to_remove = _related_removal(solution, removal_fraction, fixed_remove_count, random_seed)
    
    if len(to_remove) == 0:
        return False

    routes = solution.routes
    
    # Destroy: remove selected customers from their routes
    for cid in to_remove:
        for r in routes:
            if cid in r.customer_ids:
                pos = r.customer_ids.index(cid)
                r.customer_ids.pop(pos)
                r.arrival_times.pop(pos)
                r.current_load -= r.customers_lookup[cid].demand
                r._recalculate_from(max(0, pos - 1))
                r.calculate_cost_inplace()
                break

    # Remove empty routes
    solution.routes = [r for r in routes if len(r.customer_ids) > 0]

    touched_routes = set()

    # Repair: reinsert each removed customer using best-fit greedy
    if not solution.routes:
        return False
    depot = solution.routes[0].depot
    capacity = solution.routes[0].vehicle_capacity
    customers_lookup = solution.routes[0].customers_lookup

    # Sort customers by time window tightness (tighter first)
    customers_with_tw = [(cid, customers_lookup[cid].due_date - customers_lookup[cid].ready_time) 
                          for cid in to_remove]
    customers_with_tw.sort(key=lambda x: x[1])  # Sort by time window width (ascending)
    sorted_to_remove = [cid for cid, _ in customers_with_tw]

    for cid in sorted_to_remove:
        inserted = False
        # Try existing routes first using best-fit
        for r in solution.routes:
            if _try_insert_customer_best_fit(r, cid):
                touched_routes.add(id(r))
                inserted = True
                break
        if not inserted:
            # Create new route if needed
            new_route = Route(depot, capacity, customers_lookup)
            if new_route.insert_inplace(cid, 0):
                solution.routes.append(new_route)
                touched_routes.add(id(new_route))
            else:
                # Could not insert anywhere; this should be rare
                return False

    # Post-repair polish: 2-opt on touched routes until local optimum
    for r in solution.routes:
        if id(r) in touched_routes:
            from operators.intra_route_2opt import intra_route_2opt_inplace
            improved = True
            while improved:
                improved = intra_route_2opt_inplace(r)

    solution.update_cost()
    return solution.total_cost < current_obj - 1e-6

    # Destroy: remove selected customers from their routes
    for cid in to_remove:
        for r in routes:
            if cid in r.customer_ids:
                pos = r.customer_ids.index(cid)
                r.customer_ids.pop(pos)
                r.arrival_times.pop(pos)
                r.current_load -= r.customers_lookup[cid].demand
                r._recalculate_from(max(0, pos - 1))
                r.calculate_cost_inplace()
                break

    # Remove empty routes
    solution.routes = [r for r in routes if len(r.customer_ids) > 0]

    touched_routes = set()

    # Repair: reinsert each removed customer
    # Use existing depot/capacity from first route
    if not solution.routes:
        return False
    depot = solution.routes[0].depot
    capacity = solution.routes[0].vehicle_capacity
    customers_lookup = solution.routes[0].customers_lookup

    for cid in to_remove:
        customer = customers_lookup[cid]
        inserted = False
        # try existing routes first
        for r in solution.routes:
            if _try_insert_customer(r, cid):
                touched_routes.add(id(r))
                inserted = True
                break
        if not inserted:
            # create new route if needed
            new_route = Route(depot, capacity, customers_lookup)
            if new_route.insert_inplace(cid, 0):
                solution.routes.append(new_route)
                touched_routes.add(id(new_route))
            else:
                # could not insert anywhere; abandon and rollback
                return False

    # Post-repair polish: 2-opt on touched routes
    for r in solution.routes:
        if id(r) in touched_routes:
            from operators.intra_route_2opt import intra_route_2opt_inplace
            intra_route_2opt_inplace(r)

    solution.update_cost()
    return solution.total_cost < current_obj - 1e-6


